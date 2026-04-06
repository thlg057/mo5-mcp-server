#!/usr/bin/env python3
"""
makefd.py - Génère une image disquette .fd bootable pour Thomson MO5
Remplace : fdfs -addBL output.fd BOOTMO.BIN program.BIN

Usage:
    python3 makefd.py output.fd program.BIN [file2.BIN ...]

Basé sur fdfs.c d'OlivierP-To8 (https://github.com/OlivierP-To8/BootFloppyDisk)
Le binaire BOOTMO.BIN est embarqué directement dans ce script.
"""

import sys
import struct
import os
import time
from pathlib import Path

# ==============================================================================
# Constantes du format disquette Thomson MO5
# ==============================================================================
SECTOR_SIZE  = 256          # octets par secteur (255 utiles)
SECTOR_BYTES = 255          # octets utiles par secteur
TRACK_SIZE   = 16 * SECTOR_SIZE   # 16 secteurs par piste
DISK_SIZE    = 80 * TRACK_SIZE    # 80 pistes
BLOCK_SIZE   = 8  * SECTOR_SIZE   # 8 secteurs par bloc
BLOCK_BYTES  = 8  * SECTOR_BYTES  # octets utiles par bloc

# Piste 20 : FAT + répertoire
FAT_OFFSET = 20 * TRACK_SIZE + SECTOR_SIZE + 1   # secteur 2 de la piste 20
DIR_OFFSET = 20 * TRACK_SIZE + 2 * SECTOR_SIZE   # secteur 3 de la piste 20

FREE_BLOCK     = 0xff
RESERVED_BLOCK = 0xfe

# ==============================================================================
# BOOTMO.BIN embarqué (compilé depuis BootMO.asm d'OlivierP-To8)
# Chargeur de boot pour Thomson MO5, max 120 octets utiles
# org $2200
# ==============================================================================
BOOTMO_BIN = bytes([
    0x00, 0x00, 0x58, 0x22, 0x00,  # header Thomson: type=0, size=0x0058, addr=0x2200
    0x10, 0xce, 0x20, 0xcc,        # lds #$20CC
    0x86, 0x20, 0x1f, 0x8b,        # lda #$20 / tfr a,dp
    0x86, 0x00, 0x97, 0x49,        # lda #0 / sta <DKDRV
    0xcc, 0x14, 0x01,              # ldd #$1401  (track 20, sector 1)
    0x8e, 0x23, 0x00,              # ldx #$2300  (Buffer_)
    0xbd, 0x22, 0x47,              # jsr ReadSector_
    0x1f, 0x12,                    # tfr x,y
    0x31, 0x2d,                    # leay 13,y
    0xbe, 0x23, 0x0c,              # ldx Buffer_+12
    0x30, 0x1b,                    # Boot_file: leax -5,x
    0x31, 0x21,                    # Boot_track: leay 1,y
    0xec, 0xa1,                    # ldd ,y++
    0x81, 0xff,                    # cmpa #$ff
    0x27, 0x0e,                    # beq Boot_exec
    0xbd, 0x22, 0x47,              # Boot_loop: jsr ReadSector_
    0x30, 0x89, 0x00, 0xff,        # leax 255,x
    0x5c,                          # incb
    0xe1, 0xa4,                    # cmpb ,y
    0x2e, 0xec,                    # bgt Boot_track
    0x20, 0xf2,                    # bra Boot_loop
    0x31, 0x3f,                    # Boot_exec: leay -1,y
    0xae, 0xa1,                    # ldx ,y++
    0x34, 0x20,                    # pshs y
    0xad, 0x84,                    # jsr ,x
    0x35, 0x20,                    # puls y
    0xae, 0xa0,                    # ldx ,y+
    0x8c, 0xff, 0xff,              # cmpx #$ffff
    0x26, 0xd7,                    # bne Boot_file
    0x3f, 0x28,                    # swi / fcb DKBOOT  (reboot)
    # ReadSector_:
    0x34, 0x06,                    # pshs a,b
    0x97, 0x4b,                    # sta <DKTRK
    0xd7, 0x4c,                    # stb <DKSEC
    0x9f, 0x4f,                    # stx <DKBUF
    0x86, 0x02,                    # lda #$02
    0x97, 0x48,                    # sta <DKOPC
    0x3f, 0x26,                    # swi / fcb DKCO
    0x35, 0x06,                    # puls a,b
    0x39,                          # rts
    # footer Thomson
    0xff, 0x00, 0x00, 0x00, 0x00,
])

# ==============================================================================
# Classe principale
# ==============================================================================
class FloppyDisk:
    def __init__(self):
        self.data = bytearray(DISK_SIZE)

    def format(self, diskname: str = None):
        """Formate la disquette (équivalent de formatDisk dans fdfs.c)."""
        # Remplissage avec 0xe5
        for i in range(DISK_SIZE):
            self.data[i] = 0xe5

        # Piste 20 entière initialisée à FREE_BLOCK
        for i in range(20 * TRACK_SIZE, 21 * TRACK_SIZE):
            self.data[i] = FREE_BLOCK

        # Nom de la disquette sur les 8 premiers octets de la piste 20
        if diskname:
            p = Path(diskname)
            stem = p.stem[:8]
            basename = stem.ljust(8)[:8]
            for i, ch in enumerate(basename):
                self.data[20 * TRACK_SIZE + i] = ord(ch)

        # Le 1er octet du secteur FAT n'est pas utilisé
        self.data[FAT_OFFSET - 1] = 0x00

        # Piste 20 réservée (2 blocs)
        self.data[FAT_OFFSET + 2 * 20]     = RESERVED_BLOCK
        self.data[FAT_OFFSET + 2 * 20 + 1] = RESERVED_BLOCK

        # Pistes 80+ à zéro dans la FAT
        for i in range(FAT_OFFSET + 80 * 2, DIR_OFFSET):
            self.data[i] = 0x00

    # ------------------------------------------------------------------
    def _find_free_block(self, used_blocks: list) -> int:
        """Trouve un bloc libre, en commençant par la fin (piste 79 → 0)."""
        # Blocs déjà référencés dans le répertoire
        in_use = []
        for entry in range(13, 14 * SECTOR_SIZE, 32):
            block = self.data[DIR_OFFSET + entry]
            if block != FREE_BLOCK:
                in_use.append(block)

        # Balayage de 79 → 0
        for i in range(79, -1, -1):
            if (self.data[FAT_OFFSET + i] == FREE_BLOCK
                    and i not in in_use
                    and i not in used_blocks):
                return i
        # Puis 80 → 159
        for i in range(80, 2 * 80):
            if (self.data[FAT_OFFSET + i] == FREE_BLOCK
                    and i not in in_use
                    and i not in used_blocks):
                return i
        return FREE_BLOCK  # disquette pleine

    def _find_free_entry(self) -> int:
        """Trouve une entrée libre dans le répertoire."""
        for i in range(0, 14 * SECTOR_SIZE, 32):
            if self.data[DIR_OFFSET + i] == FREE_BLOCK:
                return i
        return -1

    def _add_file_entry(self, filename: str, block: int, size_left: int) -> int:
        """Écrit une entrée de répertoire Thomson (32 octets)."""
        entry = DIR_OFFSET + self._find_free_entry()
        name = Path(filename).stem
        ext  = Path(filename).suffix.lstrip('.')

        # Nom (8 octets, complété par des espaces)
        for i in range(8):
            self.data[entry + i] = ord(name[i]) if i < len(name) else 0x20

        # Extension (3 octets)
        for i in range(3):
            self.data[entry + 8 + i] = ord(ext[i]) if i < len(ext) else 0x20

        # Type : 2 = programme assembleur (.BIN, .CHG, .MAP), 0 = BASIC sinon
        upper_ext = Path(filename).suffix.upper()
        file_type = 2 if upper_ext in ('.BIN', '.CHG', '.MAP') else 0
        self.data[entry + 11] = file_type

        # Type données : 0 = binaire
        self.data[entry + 12] = 0x00

        # Premier bloc
        self.data[entry + 13] = block

        # Nombre d'octets dans le dernier secteur (big-endian)
        self.data[entry + 14] = (size_left >> 8) & 0xff
        self.data[entry + 15] = size_left & 0xff

        # Commentaire (1 octet nul + 7 espaces)
        self.data[entry + 16] = 0x00
        for i in range(1, 8):
            self.data[entry + 16 + i] = 0x20

        # Date (jour, mois, année sur 2 chiffres)
        t = time.localtime()
        self.data[entry + 24] = t.tm_mday
        self.data[entry + 25] = t.tm_mon
        self.data[entry + 26] = t.tm_year - 2000
        for i in range(3, 8):
            self.data[entry + 24 + i] = 0x00

        return entry

    def _write_block(self, block: int, file_bytes: bytes, file_size: int, offset: int):
        """Écrit jusqu'à 8 secteurs de données dans un bloc."""
        for b in range(8):
            src = offset + b * SECTOR_BYTES
            dst = block * BLOCK_SIZE + b * SECTOR_SIZE
            nb = SECTOR_BYTES
            if src + SECTOR_BYTES > file_size:
                nb = file_size - src
            if nb > 0:
                self.data[dst:dst + nb] = file_bytes[src:src + nb]
                for j in range(nb, SECTOR_SIZE):
                    self.data[dst + j] = 0x00

    def add_file_content(self, filename: str, file_bytes: bytes):
        """Alloue des blocs et écrit le contenu d'un fichier sur la disquette."""
        size = len(file_bytes)
        blocks = []
        offset = 0
        size_left = size

        while size_left > 0:
            block = self._find_free_block(blocks)
            self._write_block(block, file_bytes, size, offset)
            offset += BLOCK_BYTES

            if blocks:
                self.data[FAT_OFFSET + blocks[-1]] = block
            blocks.append(block)

            if size_left < BLOCK_BYTES:
                # Dernier bloc : calcul du nombre de secteurs occupés
                nb_sectors = 0xc0
                remaining = size_left
                while remaining > 0:
                    nb_sectors += 1
                    remaining -= SECTOR_BYTES
                self.data[FAT_OFFSET + blocks[-1]] = nb_sectors
                actual_size_left = size_left - SECTOR_BYTES * (nb_sectors - 0xc0 - 1)
                if actual_size_left <= 0:
                    actual_size_left = size_left % SECTOR_BYTES
                    if actual_size_left == 0:
                        actual_size_left = SECTOR_BYTES
                self._add_file_entry(filename, blocks[0], actual_size_left)

            size_left -= BLOCK_BYTES

    def add_file(self, filepath: str):
        """
        Charge un fichier .BIN et l'ajoute à la disquette.
        Ajoute le header/footer Thomson si absent.
        """
        filename = os.path.basename(filepath)
        with open(filepath, 'rb') as f:
            raw = f.read()

        size = len(raw)
        file_bytes = bytearray(raw)

        if filepath.upper().endswith('.BIN'):
            # Vérifie la présence du header Thomson (5 octets) et footer (5 octets)
            if size >= 10:
                size_cont = size - 10
                has_header = (raw[0] == 0x00
                              and raw[1] == (size_cont >> 8) & 0xff
                              and raw[2] == size_cont & 0xff)
            else:
                has_header = False

            if not has_header:
                print(f"  /!\\ Pas de header Thomson dans {filename}, ajout automatique impossible sans adresse.")
                print(f"      Utilisez la syntaxe CMOC qui génère un .BIN avec header.")
                # On laisse passer tel quel (CMOC génère un BIN avec header)

        print(f"  Ajout de {filename} ({size} octets)")
        self.add_file_content(filename, bytes(file_bytes))

    # ------------------------------------------------------------------
    def add_boot_loader(self, nb_files: int):
        """
        Écrit le boot loader dans le secteur 1 de la piste 20,
        et les descripteurs de fichiers (adresse, pistes/secteurs) à partir de l'octet 12.
        Équivalent de addBootLoader() dans fdfs.c.
        """
        boot = BOOTMO_BIN
        size = len(boot)

        if size > 130:
            raise ValueError(f"BOOTMO.BIN trop grand ({size} octets, max 120 utiles)")

        # Vérification de l'adresse de boot : doit commencer à $6200 ou $2200
        if not ((boot[0] == 0x00)
                and (boot[3] in (0x62, 0x22))
                and (boot[4] == 0x00)):
            raise ValueError("BOOTMO.BIN invalide : doit commencer à l'adresse $6200 ou $2200")

        # Écriture du secteur de boot (sector 1, track 0, position 0 dans le .fd)
        # On réinitialise les 256 premiers octets du fichier
        for i in range(SECTOR_SIZE):
            self.data[i] = 0x00

        checksum = 0x55
        content_size = size - 10  # sans header ni footer
        for i in range(content_size):
            self.data[i] = (256 - boot[i + 5]) & 0xff
            checksum = (checksum + boot[i + 5]) & 0xff

        # Signature "BASIC2" à l'offset 120
        for i, ch in enumerate(b'BASIC2'):
            self.data[120 + i] = ch

        checksum = (checksum + 0x6c) & 0xff
        self.data[127] = checksum

        # Marque le bloc 0 comme réservé dans la FAT
        self.data[FAT_OFFSET] = RESERVED_BLOCK

        # Construction des descripteurs de fichiers dans la piste 20, à partir de l'octet 12
        n = 12
        base = 20 * TRACK_SIZE

        for f_idx in range(nb_files):
            entry = f_idx * 32

            block = self.data[DIR_OFFSET + entry + 13]

            # Lecture du header Thomson du fichier pour extraire adresse de chargement
            file_addr = (self.data[block * BLOCK_SIZE + 3] << 8) | self.data[block * BLOCK_SIZE + 4]
            file_size = (self.data[block * BLOCK_SIZE + 1] << 8) | self.data[block * BLOCK_SIZE + 2]

            print(f"  Fichier #{f_idx}: addr=${file_addr:04x} taille={file_size} octets")

            # Adresse de chargement (2 octets)
            self.data[base + n] = (file_addr >> 8) & 0xff
            n += 1
            self.data[base + n] = file_addr & 0xff
            n += 1

            # Parcours des blocs du fichier
            file_exec = 0
            current_block = block
            src = 0

            while current_block != FREE_BLOCK:
                next_b = self.data[FAT_OFFSET + current_block]
                nbs = 8
                if next_b > 0xc0:
                    nbs = next_b - 0xc0
                    next_b = FREE_BLOCK
                    # Récupère l'adresse d'exécution dans le footer Thomson
                    nb_bytes = (self.data[DIR_OFFSET + entry + 14] << 8) | self.data[DIR_OFFSET + entry + 15]
                    src = current_block * BLOCK_SIZE + (nbs - 1) * SECTOR_SIZE + nb_bytes
                    if nb_bytes < 2:
                        file_exec = self.data[src - 3]
                    else:
                        file_exec = self.data[src - 2]
                    file_exec = (file_exec << 8) | self.data[src - 1]
                    print(f"    exec=${file_exec:04x}")

                track  = current_block >> 1
                sector = 9 if (current_block & 0x01) else 1

                self.data[base + n] = track;      n += 1
                self.data[base + n] = sector;     n += 1
                self.data[base + n] = sector + nbs - 1; n += 1

                current_block = next_b

            # Marqueur de fin de fichier + adresse d'exécution
            self.data[base + n] = FREE_BLOCK;              n += 1
            self.data[base + n] = (file_exec >> 8) & 0xff; n += 1
            self.data[base + n] = file_exec & 0xff;         n += 1

    # ------------------------------------------------------------------
    def save(self, path: str):
        with open(path, 'wb') as f:
            f.write(self.data)
        print(f"✓ Image .fd écrite : {path} ({DISK_SIZE} octets)")


# ==============================================================================
# Point d'entrée
# ==============================================================================
def main():
    if len(sys.argv) < 3:
        print("Usage: python3 makefd.py output.fd program.BIN [file2.BIN ...]")
        print("")
        print("  Génère une image disquette .fd bootable pour Thomson MO5.")
        print("  Remplace : fdfs -addBL output.fd BOOTMO.BIN program.BIN")
        print("  Le boot loader MO5 est embarqué dans ce script.")
        sys.exit(1)

    output_fd  = sys.argv[1]
    input_bins = sys.argv[2:]

    print(f"=== Génération de {output_fd} ===")
    disk = FloppyDisk()
    disk.format(output_fd)

    print("--- Ajout des fichiers ---")
    for bin_path in input_bins:
        disk.add_file(bin_path)

    print("--- Écriture du boot loader MO5 ---")
    disk.add_boot_loader(len(input_bins))

    os.makedirs(os.path.dirname(os.path.abspath(output_fd)), exist_ok=True)
    disk.save(output_fd)


if __name__ == '__main__':
    main()

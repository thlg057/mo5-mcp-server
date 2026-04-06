#!/usr/bin/env python3
"""
Convertit une image disquette .fd (3.5" 720Ko) en .sd (5.25" 320Ko)
pour Thomson MO5/TO7
Basé sur le code C d'OlivierP-To8
https://github.com/OlivierP-To8/InufutoPorts/blob/main/Thomson/fdtosd.c
"""

import sys
import os

def fd_to_sd(fd_path, sd_path):
    """Convertit un fichier .fd en .sd"""
    
    sector_buffer = bytearray(256)
    empty = bytes([0xFF] * 512)
    
    try:
        with open(fd_path, 'rb') as fd, open(sd_path, 'wb') as sd:
            # 4 faces * 80 pistes = 320 pistes
            for track in range(4 * 80):
                # 16 secteurs par piste
                for sector in range(1, 17):
                    data = fd.read(256)
                    if len(data) == 256:
                        # Écrire le secteur + padding vide
                        sd.write(data)
                        sd.write(empty[:256])
                    else:
                        # Secteur manquant = remplir de 0xFF
                        sd.write(empty)
        
        print(f"✓ Conversion réussie: {sd_path}")
        return True
        
    except FileNotFoundError:
        print(f"✗ Erreur: impossible d'ouvrir {fd_path}")
        return False
    except Exception as e:
        print(f"✗ Erreur lors de la conversion: {e}")
        return False

def main():
    if len(sys.argv) != 4 or sys.argv[1] != '-conv':
        print(f"Usage: {sys.argv[0]} -conv disk.fd disk.sd")
        sys.exit(1)
    
    fd_path = sys.argv[2]
    sd_path = sys.argv[3]
    
    if not os.path.exists(fd_path):
        print(f"✗ Erreur: le fichier {fd_path} n'existe pas")
        sys.exit(1)
    
    success = fd_to_sd(fd_path, sd_path)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
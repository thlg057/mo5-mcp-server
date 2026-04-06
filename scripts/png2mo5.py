#!/usr/bin/env python3
"""
Convertisseur PNG vers sprite Thomson MO5

Convertit une image PNG en tableaux C pour le Thomson MO5
Format: 1 octet = 8 pixels de 1 bit (forme/fond)
Génère 2 tableaux: FORME (bitmap) et COULEUR (attributs par groupe de 8 pixels)

Usage:
    python png_to_mo5_v2.py image.png [--name SPRITE_NAME] [--bg-color 0-15] [--transparent]
"""

import argparse
import sys
import os
from pathlib import Path
try:
    from PIL import Image
except ImportError:
    print("Erreur: PIL (Pillow) n'est pas installé.")
    print("Installez-le avec: pip install Pillow")
    sys.exit(1)

# Palette MO5 complète (16 couleurs, RGB approximatif)
MO5_PALETTE = {
    0:  {'R': 0,   'G': 0,   'B': 0,   'Name': 'C_BLACK'},
    1:  {'R': 255, 'G': 0,   'B': 0,   'Name': 'C_RED'},
    2:  {'R': 0,   'G': 255, 'B': 0,   'Name': 'C_GREEN'},
    3:  {'R': 255, 'G': 255, 'B': 0,   'Name': 'C_YELLOW'},
    4:  {'R': 0,   'G': 0,   'B': 255, 'Name': 'C_BLUE'},
    5:  {'R': 255, 'G': 0,   'B': 255, 'Name': 'C_MAGENTA'},
    6:  {'R': 0,   'G': 255, 'B': 255, 'Name': 'C_CYAN'},
    7:  {'R': 255, 'G': 255, 'B': 255, 'Name': 'C_WHITE'},
    8:  {'R': 128, 'G': 128, 'B': 128, 'Name': 'C_GRAY'},
    9:  {'R': 255, 'G': 128, 'B': 128, 'Name': 'C_LIGHT_RED'},
    10: {'R': 128, 'G': 255, 'B': 128, 'Name': 'C_LIGHT_GREEN'},
    11: {'R': 255, 'G': 255, 'B': 128, 'Name': 'C_LIGHT_YELLOW'},
    12: {'R': 128, 'G': 128, 'B': 255, 'Name': 'C_LIGHT_BLUE'},
    13: {'R': 255, 'G': 128, 'B': 255, 'Name': 'C_PURPLE'},
    14: {'R': 128, 'G': 255, 'B': 255, 'Name': 'C_LIGHT_CYAN'},
    15: {'R': 255, 'G': 128, 'B': 0,   'Name': 'C_ORANGE'}
}


def get_color_distance(r1, g1, b1, r2, g2, b2):
    """Calcule la distance euclidienne entre deux couleurs RGB"""
    return (r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2


def get_closest_mo5_color(r, g, b, a):
    """Trouve la couleur MO5 la plus proche d'une couleur RGBA donnée"""
    # Si transparent, retourner None
    if a < 128:
        return None
    
    min_distance = float('inf')
    closest_color = 0
    
    for color_idx in range(16):
        palette = MO5_PALETTE[color_idx]
        distance = get_color_distance(r, g, b, palette['R'], palette['G'], palette['B'])
        
        if distance < min_distance:
            min_distance = distance
            closest_color = color_idx
    
    return closest_color


def get_dominant_colors(pixels, default_bg):
    """Détermine les 2 couleurs dominantes d'un groupe de 8 pixels"""
    # Compter les occurrences de chaque couleur
    color_count = {}
    
    for pixel in pixels:
        r, g, b, a = pixel
        if a < 128:
            continue
        
        color = get_closest_mo5_color(r, g, b, a)
        if color is not None:
            color_count[color] = color_count.get(color, 0) + 1
    
    # Si pas de pixels visibles, retourner couleur par défaut
    if not color_count:
        return {
            'Background': default_bg,
            'Foreground': default_bg,
            'IsSingleColor': True
        }
    
    # Si une seule couleur
    if len(color_count) == 1:
        color = list(color_count.keys())[0]
        return {
            'Background': default_bg,
            'Foreground': color,
            'IsSingleColor': True
        }
    
    # Le fond est toujours default_bg — chercher la couleur fg la plus fréquente
    # parmi les couleurs non-fond
    non_bg = {c: n for c, n in color_count.items() if c != default_bg}

    if not non_bg:
        # Toutes les couleurs du bloc sont le fond
        return {
            'Background': default_bg,
            'Foreground': default_bg,
            'IsSingleColor': True
        }

    fg = max(non_bg, key=lambda c: non_bg[c])

    return {
        'Background': default_bg,
        'Foreground': fg,
        'IsSingleColor': False
    }

def get_dominant_colors_transparent(pixels):
    """Version spécifique : force le fond à 0 pour mo5_sprite_bg"""
    color_count = {}
    for pixel in pixels:
        r, g, b, a = pixel
        if a < 128: continue
        color = get_closest_mo5_color(r, g, b, a)
        if color is not None:
            color_count[color] = color_count.get(color, 0) + 1
    if not color_count:
        return {'Background': 0, 'Foreground': 0, 'IsSingleColor': True}
    sorted_colors = sorted(color_count.items(), key=lambda x: x[1], reverse=True)
    fg = sorted_colors[0][0]
    return {'Background': 0, 'Foreground': fg, 'IsSingleColor': True}

def convert_png_to_mo5_sprite(image_path, sprite_name=None, default_bg=0, quiet=False, transparent=False):
    """Convertit une image PNG en sprite MO5"""

    if not os.path.exists(image_path):
        print(f"[ERREUR] Le fichier '{image_path}' n'existe pas.")
        return None

    if not quiet:
        print(f"[INFO] Chargement de l'image: {image_path}")

    try:
        img = Image.open(image_path)
        # Convertir en RGBA si nécessaire
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
    except Exception as e:
        print(f"[ERREUR] Erreur lors du chargement: {e}")
        return None

    width, height = img.size
    if not quiet:
        print(f"       Dimensions: {width}x{height} pixels")

    # Vérifier que la largeur est multiple de 8
    original_width = width
    if width % 8 != 0:
        if not quiet:
            print(f"[ATTENTION] Largeur ({width}) non multiple de 8.")
        width = (width // 8) * 8
        if not quiet:
            print(f"            Ajustée à {width} pixels")
    
    bytes_per_line = width // 8
    
    # Gérer le nom du sprite et le chemin de sortie
    output_path = None
    if sprite_name:
        # Si un nom est fourni, il peut contenir un chemin
        name_path = Path(sprite_name)
        output_path = name_path  # Conserver le chemin complet pour la sortie
        sprite_name = name_path.stem  # Extraire juste le nom pour les variables C
    else:
        sprite_name = Path(image_path).stem
    
    # Remplacer les caractères non alphanumériques par des underscores (pour les noms de variables C)
    sprite_name_clean = ''.join(c if c.isalnum() or c == '_' else '_' for c in sprite_name)

    if not quiet:
        print("[INFO] Analyse de l'image...")

    # Tableaux pour stocker les données
    form_data = []
    color_data = []
    color_stats = {}
    total_blocks = 0
    multi_color_blocks = 0
    
    # Charger tous les pixels
    pixels = img.load()
    
    # Traiter chaque ligne
    for y in range(height):
        line_form_bytes = []
        line_color_bytes = []
        visual = ""
        
        # Traiter les pixels 8 par 8
        for x in range(0, width, 8):
            # Récupérer les 8 pixels
            pixel_group = []
            for i in range(8):
                if x + i < width:
                    pixel_group.append(pixels[x + i, y])
                else:
                    pixel_group.append((0, 0, 0, 0))
            
            # Déterminer les 2 couleurs dominantes
            if transparent:
                colors = get_dominant_colors_transparent(pixel_group)
            else:
                colors = get_dominant_colors(pixel_group, default_bg)
                
            bg = colors['Background']
            fg = colors['Foreground']
            
            total_blocks += 1
            if not colors['IsSingleColor']:
                multi_color_blocks += 1
            
            # Statistiques
            color_key = f"{bg}-{fg}"
            color_stats[color_key] = color_stats.get(color_key, 0) + 1
            
            # Créer l'octet de COULEUR (FFFFBBBB: Forme en haut, Fond en bas)
            color_byte = (bg & 0x0F) | ((fg & 0x0F) << 4)
            line_color_bytes.append(f"0x{color_byte:02X}")
            
            # Créer l'octet de FORME (bitmap: 1=forme, 0=fond)
            form_byte = 0
            for i in range(8):
                if x + i < width:
                    pixel = pixel_group[i]
                    r, g, b, a = pixel
                    
                    if a < 128:
                        # Transparent = fond (bit 0)
                        pixel_bit = 0
                        visual += "-"
                    else:
                        # Déterminer si c'est la couleur de forme ou de fond
                        pixel_color = get_closest_mo5_color(r, g, b, a)
                        
                        if pixel_color is not None:
                            if fg == bg:
                                # Bloc monochrome fond : tous les pixels = fond
                                pixel_bit = 0
                                visual += "-"
                            else:
                                # Si la couleur est plus proche de fg que de bg
                                dist_fg = get_color_distance(r, g, b,
                                                            MO5_PALETTE[fg]['R'],
                                                            MO5_PALETTE[fg]['G'],
                                                            MO5_PALETTE[fg]['B'])
                                dist_bg = get_color_distance(r, g, b,
                                                            MO5_PALETTE[bg]['R'],
                                                            MO5_PALETTE[bg]['G'],
                                                            MO5_PALETTE[bg]['B'])

                                if dist_fg < dist_bg:
                                    pixel_bit = 1  # Forme
                                    visual += "█"
                                else:
                                    pixel_bit = 0  # Fond
                                    visual += "-"
                        else:
                            pixel_bit = 0
                            visual += "-"
                    
                    # Positionner le bit (MSB = pixel de gauche)
                    shift = 7 - i
                    form_byte |= (pixel_bit << shift)
                else:
                    visual += "-"
            
            line_form_bytes.append(f"0x{form_byte:02X}")
        
        # Ajouter les lignes
        form_line = "    " + ", ".join(line_form_bytes)
        color_line = "    " + ", ".join(line_color_bytes)
        
        if y < height - 1:
            form_line += ","
            color_line += ","
        
        form_line += f"  // {y}  {visual}"
        color_line += f"  // {y}"
        
        form_data.append(form_line)
        color_data.append(color_line)
    
    # Construire le code C avec include guards
    guard_name = f"SPRITE_{sprite_name_clean.upper()}_H"

    output = []
    output.append(f"#ifndef {guard_name}")
    output.append(f"#define {guard_name}")
    output.append("")
    output.append("// =============================================")
    output.append(f"// Sprite: {sprite_name_clean}")
    output.append(f"// Source: {os.path.basename(image_path)}")
    output.append(f"// Taille: {width}x{height} pixels ({bytes_per_line} octets x {height} lignes)")
    output.append("// Format: 1 octet = 8 pixels (1 bit/pixel)")
    output.append("// Contrainte: 2 couleurs par groupe de 8 pixels")
    output.append("// =============================================")
    output.append("")

    # Ajouter les defines pour les dimensions
    output.append(f"#define SPRITE_{sprite_name_clean.upper()}_WIDTH_BYTES {bytes_per_line}")
    output.append(f"#define SPRITE_{sprite_name_clean.upper()}_HEIGHT {height}")
    output.append("")

    output.append("// Données de FORME (bitmap: 1=forme, 0=fond)")
    output.append(f"unsigned char sprite_{sprite_name_clean}_form[{bytes_per_line * height}] = {{")
    output.extend(form_data)
    output.append("};")
    output.append("")
    output.append("// Données de COULEUR (attributs par groupe de 8 pixels)")
    output.append("// Format: FFFFBBBB (Forme bits 4-7, Fond bits 0-3)")
    output.append(f"unsigned char sprite_{sprite_name_clean}_color[{bytes_per_line * height}] = {{")
    output.extend(color_data)
    output.append("};")
    output.append("")
    output.append(f"// Taille totale: {bytes_per_line * height} octets par tableau")

    if total_blocks > 0:
        percentage = round(multi_color_blocks * 100.0 / total_blocks, 1)
        output.append(f"// Blocs multi-couleurs: {multi_color_blocks} / {total_blocks} ({percentage}%)")
    output.append("")

    if color_stats:
        output.append("// Combinaisons de couleurs utilisées:")
        for key in sorted(color_stats.keys()):
            parts = key.split('-')
            bg = int(parts[0])
            fg = int(parts[1])
            count = color_stats[key]
            bg_name = MO5_PALETTE[bg]['Name']
            fg_name = MO5_PALETTE[fg]['Name']
            output.append(f"//   Fond={bg_name}, Forme={fg_name} : {count} blocs de 8 pixels")
        output.append("")

    # Macro d'initialisation MO5_Sprite
    sn = sprite_name_clean
    SN = sprite_name_clean.upper()
    output.append(f"// Macro d'initialisation pour MO5_Sprite (voir mo5_sprite.h)")
    output.append(f"#define SPRITE_{SN}_INIT \\")
    output.append(f"    {{ sprite_{sn}_form, sprite_{sn}_color, \\")
    output.append(f"      SPRITE_{SN}_WIDTH_BYTES, SPRITE_{SN}_HEIGHT }}")
    output.append("")
    output.append(f"// Utilisation:")
    output.append(f"//   MO5_Sprite sprite_{sn} = SPRITE_{SN}_INIT;")
    output.append("")
    output.append(f"#endif // {guard_name}")
    
    img.close()
    
    return {
        'Code': '\n'.join(output),
        'SpriteName': sprite_name_clean,
        'OutputPath': output_path,  # Chemin de sortie si spécifié
        'Width': width,
        'Height': height,
        'BytesPerLine': bytes_per_line,
        'ColorStats': color_stats,
        'MultiColorBlocks': multi_color_blocks,
        'TotalBlocks': total_blocks
    }


def main():
    parser = argparse.ArgumentParser(
        description='Convertisseur PNG vers sprite Thomson MO5',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python png_to_mo5_v2.py mon_sprite.png
  python png_to_mo5_v2.py hero.png --name hero --bg-color 4
        """
    )
    
    parser.add_argument('image_path', help='Chemin vers l\'image PNG à convertir')
    parser.add_argument('--name', dest='sprite_name', help='Nom du sprite (optionnel)')
    parser.add_argument('--bg-color', dest='bg_color', type=int, default=0,
                       choices=range(16), metavar='0-15',
                       help='Couleur de fond par défaut (0-15, défaut: 0=noir)')
    parser.add_argument('--transparent', action='store_true',
                       help='Force le fond à 0 pour mo5_sprite_bg')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Mode silencieux (affiche uniquement le message final)')

    args = parser.parse_args()

    if not args.quiet:
        print()
        print("=" * 60)
        print("  Convertisseur PNG -> Sprite Thomson MO5 (Multi-couleurs)")
        print("  Format: 1 octet = 8 pixels (1 bit/pixel)")
        print("  2 couleurs auto-détectées par groupe de 8 pixels")
        print("=" * 60)
        print()

    result = convert_png_to_mo5_sprite(args.image_path, args.sprite_name, args.bg_color, args.quiet, args.transparent)
    
    if result:
        if not args.quiet:
            # Afficher le résultat
            print("=" * 60)
            print(result['Code'])
            print("=" * 60)
            print()
            print("[OK] Sprite généré avec succès!")
            print()
            print("[INFO] Le sprite utilise 2 tableaux:")
            print(f"       - sprite_{result['SpriteName']}_form  (bitmap 1 bit/pixel)")
            print(f"       - sprite_{result['SpriteName']}_color (attributs couleur)")
            print()
            print("[STATS] Analyse:")
            print(f"        Blocs multi-couleurs: {result['MultiColorBlocks']}/{result['TotalBlocks']}")
            if result['TotalBlocks'] > 0:
                percentage = round(result['MultiColorBlocks'] * 100.0 / result['TotalBlocks'], 1)
                print(f"        Pourcentage: {percentage}%")
            print()
            print("[INFO] Utilisation:")
            print(f"       draw_sprite_multicolor(x, y,")
            print(f"                              sprite_{result['SpriteName']}_form,")
            print(f"                              sprite_{result['SpriteName']}_color,")
            print(f"                              {result['BytesPerLine']}, {result['Height']});")
            print()

        # Sauvegarder
        if result['OutputPath']:
            # Si --name a été spécifié, utiliser ce chemin
            output_path = result['OutputPath']
            # Si pas d'extension .c ou .h, ajouter .c
            if output_path.suffix not in ['.c', '.h']:
                output_path = output_path.with_suffix('.c')
            # Créer les répertoires parents si nécessaire
            output_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            # Sinon, créer dans le même répertoire que l'image source
            source_path = Path(args.image_path)
            output_path = source_path.parent / (source_path.stem + '_sprite_mc.c')

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result['Code'])

        if not args.quiet:
            print(f"[OK] Sprite sauvegardé dans: {output_path}")
            print()

        # Tenter de copier dans le presse-papier (optionnel)
        if not args.quiet:
            try:
                import pyperclip
                pyperclip.copy(result['Code'])
                print("[OK] Code copié dans le presse-papier!")
            except ImportError:
                pass  # pyperclip n'est pas installé, ce n'est pas grave
            except Exception:
                pass  # Échec de la copie, ce n'est pas grave

        # Message final (toujours affiché, même en mode quiet)
        print(f"[OK] Fichier généré: {output_path}")
    else:
        print("[ERREUR] Échec de la conversion")
        sys.exit(1)

    if not args.quiet:
        print()


if __name__ == '__main__':
    main()
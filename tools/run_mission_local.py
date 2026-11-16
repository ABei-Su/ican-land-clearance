"""Development entry point; uses current source and installed package assets."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/land_clearance'))
from land_clearance.mission_node import main

if __name__ == '__main__':
    main()

import unittest
import sys
from pathlib import Path

def run_all_tests():
    # Add the current directory to sys.path to allow imports from 'tests'
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if not result.wasSuccessful():
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()

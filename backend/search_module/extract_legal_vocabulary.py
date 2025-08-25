#!/usr/bin/env python3
"""
Legal Vocabulary Extraction - Smart Runner
=========================================

Automatically extracts vocabulary from legal cases.
- Processes new data efficiently
- Uses optimal settings
- Handles future data scraping automatically

Just run: python extract_legal_vocabulary.py
"""

import os
import sys
import subprocess

def main():
    """Run legal vocabulary extraction with smart processing"""
    print("🏛️ Starting Legal Vocabulary Extraction...")
    print("   Smart processing: Only new data will be processed")
    print("   For complete reprocessing, use: python manage.py extract_legal_vocabulary --force")
    print()
    
    try:
        # Run with --only-new for efficient processing of new data
        result = subprocess.run([
            sys.executable, 'manage.py', 'extract_legal_vocabulary', '--only-new'
        ], capture_output=False, text=True, check=True)
        
        print("\n🎉 Legal vocabulary extraction completed successfully!")
        print("📊 Your legal vocabulary database is now ready for use!")
        print("\n💡 Tips for future data:")
        print("   • Run this same command after scraping new data")
        print("   • It will automatically process only new cases")
        print("   • For complete reprocessing, add --force flag")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

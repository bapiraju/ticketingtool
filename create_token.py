#!/usr/bin/env python
"""
Quick token generation utility for testing.
Usage: python create_token.py [--role ROLE] [--subject SUBJECT]
"""

import sys
from app.core.token import create_token


def main():
    role = "admin"
    subject = "admin1"
    
    # Simple arg parsing
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--role" and i + 2 < len(sys.argv):
            role = sys.argv[i + 2]
        elif arg == "--subject" and i + 2 < len(sys.argv):
            subject = sys.argv[i + 2]
    
    token = create_token(role=role, subject=subject, expires_seconds=3600)
    print(token)


if __name__ == "__main__":
    main()
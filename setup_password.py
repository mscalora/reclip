#!/usr/bin/env python3
import json
import os
import getpass
import bcrypt

def main():
    print("=== ReClip Password Setup ===")
    
    while True:
        password = getpass.getpass("Enter a secure password for the web UI: ")
        confirm_password = getpass.getpass("Confirm password: ")

        if password != confirm_password:
            print("Passwords do not match. Please try again.\n")
            continue
            
        if not password:
            print("Password cannot be empty. Please try again.\n")
            continue
            
        break

    print("Generating bcrypt hash...")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    config = {
        "admin_password_hash": hashed
    }

    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        
    print(f"\nSuccess! Configuration saved to {config_path}")
    print("You can now start the ReClip server.")

if __name__ == "__main__":
    main()

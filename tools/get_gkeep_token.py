import gpsoauth
import getpass
import sys

def get_master_token():
    print("--- Google Keep Master Token Generator ---")
    print("This script will help you obtain the token needed for the 'gkeep' backend.")
    print("IMPORTANT: Google is retiring password-based login support.")
    print("If you have 2-Step Verification (2FA) enabled:")
    print("1. You MUST use an 'App Password'.")
    print("2. Create it at: https://myaccount.google.com/apppasswords\n")
    
    email = input("Google Email (e.g.: user@gmail.com): ")
    if "@" not in email:
        email += "@gmail.com"
        
    password = getpass.getpass("Password (or 16-letter App Password): ").replace(" ", "")

    print(f"\nRequesting Master Token for {email}...")
    try:
        # Use a stable Android ID for gpsoauth
        android_id = '9774d56d682e549c' 
        
        res = gpsoauth.perform_master_login(email, password, android_id=android_id)
        
        if 'Token' in res:
            token = res['Token']
            print("\n" + "="*60)
            print("SUCCESS: Your Master Token has been generated:")
            print(f"\n{token}\n")
            print("="*60)
            print("Copy the token above and paste it into your .env file:")
            print(f"GOOGLE_KEEP_MASTER_TOKEN=\"{token}\"")
            print("="*60)
            print("\nIMPORTANT: Do not share this token with anyone.")
        else:
            print("\n" + "!"*30)
            print("Google Authentication Error")
            print(f"Detail: {res}")
            print("!"*30)
            
            if res.get('Error') == 'BadAuthentication':
                print("\nPOSSIBLE SOLUTIONS:")
                print("1. Verify your App Password is correct (16 letters, no spaces).")
                print("2. Ensure 2FA is enabled on your account.")
                print("3. Go here to allow access: https://accounts.google.com/DisplayUnlockCaptcha")
                print("4. Check if you received an email from Google blocking access.")
            elif res.get('Error') == 'NeedsBrowser':
                print("\nGoogle requires you to verify your identity in a browser.")
                print("Go here: https://accounts.google.com/DisplayUnlockCaptcha")

    except Exception as e:
        print(f"\nCritical script error: {str(e)}")

if __name__ == "__main__":
    try:
        get_master_token()
    except KeyboardInterrupt:
        print("\n\nProcess cancelled by user.")
        sys.exit(0)

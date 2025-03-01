from main_lib import FingerprintSensor

tries = 0
while True:
    tries += 1
    print(f"Attempt #{tries}")
    
    print("Place finger on sensor...")
    fingerprint_check = FingerprintSensor().find_fingerprint()
    
    if fingerprint_check:
        print("Access granted!")
        break
    
    if tries == 3:
        print("Too many tries. Exiting...")
        break
    if input("Try again? (y/n): ").lower() != 'y':
        break

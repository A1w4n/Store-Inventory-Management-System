import hashlib 

# functions declaration and initialization
def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode('utf-8')).hexdigest()

user_input = int(input("Enter a 4-digit PIN: "))
hashed_pin = hash_pin(str(user_input))

print('Typed PIN: ', user_input)
print('Hashed PIN: ', hashed_pin)
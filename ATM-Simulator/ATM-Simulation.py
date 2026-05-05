import openpyxl # for accessing the excel file
import hashlib # for securing the pin number
import os # for storing the transaction history in a text file
from datetime import datetime # for recording the transaction history

#   NOTE: The file paths in this code are specific to the user's system. When the code is run on a different system, the file paths should be updated accordingly.
#      - The Excel file "atmData.xlsx" is currently located at "C:\Users\orens\Documents\Coding Python\ATM-Simulator\atmData.xlsx". Change this path to the location where the Excel file is stored on your system.
#      - The transaction history text files are currently stored in "C:\Users\orens\Documents\Coding Python\ATM-Simulator". Change this path to the desired location where you want to store the transaction history files on your system.

# functions declaration and initialization
def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode('utf-8')).hexdigest()

def recorder(userAccountNumber, action, amount=None, balance=None):
    file_location = "C:\\Users\\orens\\Documents\\Coding Python\\ATM-Simulator"
    filename = os.path.join (file_location, f"{userAccountNumber}_records.txt")
    timestamp = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
    log_time = f"[{timestamp}] Action: {action}"
    if amount is not None:
        log_time += f", Amount: Php {amount}"
    if balance is not None:
       log_time += f", New Balance: Php {balance}" 

    log_time += "\n"
    with open(filename, "a") as file:
        file.write(log_time)

def create_receipt(userAccountNumber, action, amount = None, balance = None):
    timestamp = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
    receipt_text = (
        "\n========== TRANSACTION RECEIPT ==========\n"
        f"Account Number : {userAccountNumber}\n"
        f"Date & Time    : {timestamp}\n"
        f"Action         : {action}\n"
    )
    if amount is not None:
        receipt_text += f"Amount         : Php {amount}\n"
    if balance is not None:
        receipt_text += f"New Balance    : Php {balance}\n"
    receipt_text += "=========================================\n"
    return receipt_text

def dataCheck(userAccountNumber):
    for row in sheet.iter_rows(values_only = True):
        if userAccountNumber == row[0]:
            return {
                "accountNumber" : row[0],
                "pin" : row[1],
                "balance" : row[2]
            }
    return None    

def updateBalance(userAccountNumber, newBalance):
    for row in sheet.iter_rows():
        if row[0].value == userAccountNumber:
            row[2].value = newBalance
            break
    wb.save("C:\\Users\\orens\\Documents\\Coding Python\\ATM-Simulator\\atmData.xlsx") 

# workbook and sheet initialization
wb = openpyxl.load_workbook("C:\\Users\\orens\\Documents\\Coding Python\\ATM-Simulator\\atmData.xlsx")
sheet = wb.active       

# main program
while True:
    print('---------' * 5)
    userAccountNumber = int(input('\n\n\nPlease enter your account number: '))
    userData = dataCheck(userAccountNumber)

    if userData:    
        userPin = int(input('Please enter your PIN: '))
        if hash_pin(str(userPin)) == userData["pin"]:    

            while True:
                print('\n')
                print('---------' * 5)
                print("Welcome to the ATM !! User :", userData["accountNumber"])
                print("1. Check deposit", "2. Deposit", "3. Withdraw", "4. View Transaction History" , "5. Exit", sep='\n')
                action = input('Please choose an option: ')

                if action == '1': # check balance
                    print("\nCurrent Balance : Php", userData["balance"]) 
                    back = input("\nPress Enter to go back to the continue ...")
                    if back == '' :
                        continue   

                elif action == '2': # deposit 
                    depositAmount = int(input('\nPlease enter the value you want to Deposit: Php '))
                    deposit = input(" You are about to deposit Php " + str(depositAmount) + ". Do you wish to Continue? (yes/no): ")
                    if deposit == 'yes':
                        userData["balance"] += depositAmount 
                        updateBalance(userData["accountNumber"], userData["balance"])
                        print("Current Balance : Php", userData["balance"])
                        recorder(userData["accountNumber"], "Deposit", amount = depositAmount, balance = userData["balance"])
                        wantReceipt = input(" Do you want a receipt? (yes/no) : ")
                        if wantReceipt == 'yes':
                            print(create_receipt(userData["accountNumber"], "Deposit", amount = depositAmount, balance = userData["balance"]))
                            break
                        elif wantReceipt == 'no':
                            break
                        else:
                            print('Please enter a VALID response!!')
                            continue
                    elif deposit == 'no':
                        continue
                    else:
                        print('Please enter a VALID response!!')
                        continue

                elif action == '3':     # withdraw
                    if userData["balance"] < 18:
                        print('\nYou are not able to withdraw since your balance is less than Php 18.0')
                        continue
                    else:
                        print('\nYour current balance will be deduced by Php 18.00')
                        withdraw = input(" Do you still wish to withdraw? (yes/no) : ")

                        if withdraw == 'yes':
                            withdrawAmount = int(input('\nPlease enter the value you want to Withdraw: Php '))
                            userData["balance"] -= withdrawAmount + 18.00
                            updateBalance(userData["accountNumber"], userData["balance"])
                            print("Current Balance : Php", userData["balance"])
                            recorder(userData["accountNumber"], "Withdraw", amount = withdrawAmount, balance = userData["balance"])
                            wantReceipt = input(" Do you want a receipt? (yes/no) : ")
                            if wantReceipt == 'yes':
                                print(create_receipt(userData["accountNumber"], "Withdraw", amount = withdrawAmount, balance = userData["balance"]))
                                break
                            elif wantReceipt == 'no':
                                break
                            else: 
                                print("Please enter a valid response!!")
                        elif withdraw == 'no':
                            continue
                        else:   
                            print('Please enter a VALID response!!')
                            continue

                elif action == '4': # view transaction history
                    file_location = "C:\\Users\\orens\\Documents\\Coding Python\\ATM-Simulator"
                    filename = os.path.join (file_location, f"{userAccountNumber}_records.txt")
                    if os.path.exists(filename):
                        with open(filename, "r") as file:
                            transaction_history = file.read()
                            print("\nTransaction History:")
                            print(transaction_history)
                    else:
                        print("\nNo transaction history found.")

                    back = input("\nPress Enter to go back to the continue ...")
                    if back == '' :
                        continue                

                elif action == '5': # exit
                    print('\nThank you!!')
                    break
                else:
                    print("Please input a valid response 1 to 5 only!!")

            back = input("\nPress Enter to go back to the exit ...")
            if back == '' :
                continue   

        else :        
            print('Incorrect PIN')
    else:
        print('User not found!!')

    back = input("\nPress Enter to go back to the exit ...")
    if back == '' :
        os.system('cls')
                        

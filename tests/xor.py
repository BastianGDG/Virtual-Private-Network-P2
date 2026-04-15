from bitarray import bitarray
string = "gg"
key = 123123712631872361872

key = bin(key)

ba_string = bitarray()

ba_string.frombytes(string.encode())
string = ba_string.to01()

print(string,key)

StringArray = []
KeyArray = []
cipherText = []

for character in string:
    StringArray.append(character)

for character in key:
    KeyArray.append(character)    

KeyArray = KeyArray[2:]

print(StringArray)
print(KeyArray)

for i in range(len(StringArray)):
    if StringArray[i] == KeyArray[i]:
        cipherText.append("0")
    elif StringArray[i] != KeyArray[i]:
        cipherText.append("1")
    else:
        pass
    
print(cipherText)
import sys
print("Hello from sandbox!")
print(f"Python version: {sys.version}")
print("Environment is properly isolated!")

# Test basic functionality
result = 42 * 2
print(f"Calculation result: {result}")

# Test file operations (should work in /work directory)
with open('/work/test_output.txt', 'w') as f:
    f.write('This file was created in the sandbox!')

print("File written successfully")
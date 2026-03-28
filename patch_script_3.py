
with open("scripts/dashboard/generate-data.py") as f:
    content = f.read()

# Since we dynamically load generate_data.py into test context, any modifications to the original file
# require a reload or modifying the tests file to reload the module correctly

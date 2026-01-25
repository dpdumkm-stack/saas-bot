"""
Create test CSV files for manual acceptance testing
"""
import os

# Create test directory
test_dir = "test_data"
os.makedirs(test_dir, exist_ok=True)

# Test 1: Tab-separated TXT (Notepad style)
with open(os.path.join(test_dir, "test_tab_separated.txt"), "w", encoding="utf-8") as f:
    f.write("628123456789\tBudi Santoso\n")
    f.write("628987654321\tAni Wijaya\n")
    f.write("628555666777\tCitra Dewi\n")

print("✅ Created: test_tab_separated.txt")

# Test 2: Simple list (one per line)
with open(os.path.join(test_dir, "test_simple_list.txt"), "w", encoding="utf-8") as f:
    f.write("628111111111\n")
    f.write("628222222222\n")
    f.write("628333333333\n")

print("✅ Created: test_simple_list.txt")

# Test 3: UTF-8 with BOM (Windows Notepad default)
with open(os.path.join(test_dir, "test_utf8_bom.txt"), "w", encoding="utf-8-sig") as f:
    f.write("628444444444,Ahmad\n")
    f.write("628555555555,Rina\n")

print("✅ Created: test_utf8_bom.txt (with BOM)")

# Test 4: Mixed phone formats (normalization test)
with open(os.path.join(test_dir, "test_mixed_formats.csv"), "w", encoding="utf-8") as f:
    f.write("phone,name\n")
    f.write("08123456789,Format_08\n")
    f.write("+6281234567890,Format_+62\n")
    f.write("62-812-345-6789,Format_Dash\n")
    f.write("62 812 345 6789,Format_Space\n")
    f.write("(62) 812-345-6789,Format_Paren\n")

print("✅ Created: test_mixed_formats.csv")

# Test 5: Semicolon delimiter (Excel Indonesia)
with open(os.path.join(test_dir, "test_semicolon.csv"), "w", encoding="utf-8") as f:
    f.write("phone;name\n")
    f.write("628666666666;Tester Satu\n")
    f.write("628777777777;Tester Dua\n")

print("✅ Created: test_semicolon.csv")

print("\n" + "="*60)
print("📁 Test Data Directory: " + os.path.abspath(test_dir))
print("="*60)
print("\nYou can now use these files for manual testing:")
print("1. test_tab_separated.txt  - Tab-delimited (Notepad)")
print("2. test_simple_list.txt    - One number per line")
print("3. test_utf8_bom.txt       - UTF-8 with BOM")
print("4. test_mixed_formats.csv  - Phone normalization test")
print("5. test_semicolon.csv      - Semicolon delimiter")
print("\n⚠️  Note: These are TEST files with FAKE numbers.")
print("    Do NOT use in real broadcasts!")

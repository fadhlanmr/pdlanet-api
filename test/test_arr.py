arr = []
arr.append(1)
arr.append(3)
arr.append(4)
for item in arr:
    print(item)

name_table = [("bob", "marley", "'e1'"), ("john", "doe", "\"e2\""), ("alice", "smith", "e3")]
for name, surname, employee_id in name_table:
    print(f"Name: {name}, Surname: {surname}, Employee ID: {employee_id}")
    
table_results = {row[0]: row[1:] for row in name_table}
print(table_results)
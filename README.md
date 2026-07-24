### X Electronics

Warehouse Management System

This app implements a stateless stock ledger with moving-average valuation: stock movements are recorded as immutable ledger entries, and balances and valuation are computed at read time.

Valuation follows the moving-average rule:
- A receipt adds qty × incoming_rate of value and shifts the average.
- A consumption removes value at the average prevailing at that moment and leaves the average unchanged.

## Screenshots
### DocTypes
![List of created DocTypes](screenshots/DocTypes.png)

### Item
![Item DocType](screenshots/Item.png)

### Warehouse Tree
![Warehouse tree](screenshots/Warehouse.png)

### Stock Ledger Entry
![Stock Ledger Entry DocType](<screenshots/Stock Ledger Entry.png>)

### Stock Entry (Parent)
![Stock Entry](<screenshots/Stock Entry.png>)

### STock Entry Item (Child)
![Stock Entry Item](<screenshots/Stock Entry Item_1.png>)
![Stock Entry Item grid view](<screenshots/Stock Entry Item (child).png>)

## Reports

### Stock Ledger Report
![Ledger Report](<screenshots/Stock Ledger Report.png>)

### Stock Balance Report
![Balance Report](<screenshots/Stock Balance Report.png>)
 
## Project Description:
The Supply Dashboard is a web application that allows our distribution centers to track shop supplies and usage across all distribution centers. This will allow us to control spending/usage and order supplies more efficiently. 

### Technologies Used:
* Django
* Fly.io
* Postgres


### Core features include:
* User Authentication System for each Distribution Center Location.
* Center based restrictions for adding and removing items. 
* Receiving supplies into pre-defined storage locations 
* Checking out items coupled with technician name for reporting on usage. 
* Home page dashboard to display all inventory across centers and a high level overview of cost and item count. 
* Links to all shop documentation via WISE and Operational Excellence sharepoint pages.
* Link to Operation Expenses report.
	* Tracks all vendors and associated costs for 2023-2024.
* Supply level breakdown across all 3 centers. 
	* Ability to breakdown by vendor.
	* Insufficient vs sufficient stock levels based on supply level thresholds per item. 
	* Ability to export insufficient items to csv to streamline ordering process.
* Technician usage reporting.
	* Can filter by start date-end date , Technician date.
	* Interactive chart with drill down capability.


### Future Updates:
* Adding user approval for supplies requests
* Additional analytics
	* Usage report by product 
	* cost breakdown by technician 
* Automated ordering for applicable vendors 
* Supply Transfers between distribution centers 
* Barcode scanning 
* Additional Analytics (Top 10 Products, Receiving per DC, etc..)
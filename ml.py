from sklearn.model_selection import train_test_split
import pandas as pd 


data = pd.read_csv("data.csv")
columns = list(data.columns)
print(columns)

'''
objective = read the data, transform data, train/test ML, create ML to use.
caveats
    - train only on `is_actuals` data. forecast data shouldn't be included
    - time might be important - have 2 ML models to test this
1. read data.csv
2. derive columns from `time` to include `month, day_of_week` - for time experiment model
3. include lag features like `temp_yesterday, pressure_change` - additional features
4. train up to `(is_actuals==True)` columns. 
5. test up to `(is_actuals==True)` columns.
6. some stats stuff i need to figure out ?
'''
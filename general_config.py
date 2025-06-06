import os, os.path as op

# City
city_id = 370200
city_abbr = "qd"
city_name = "青岛"

# Task
main_tasks = ["ershoufang", "zufang"]    # including json/csv/preprocess files
sub_tasks = ["city_info", "complement", "xiaoqu_pos"]  # including json file only

# Files
data_dir = "../data"
json_file = op.join(data_dir, "{}_{}.json")               # 1 for city_abbr, 2 for task from main_tasks & sub_tasks
csv_file = op.join(data_dir, "{}_{}.csv")
proc_file = op.join(data_dir, "{}_{}_preprocessed.csv")
cluster_file = op.join(data_dir, "{}_{}_cluster.csv")
# Create dir
if not op.exists(data_dir):
    os.makedirs(data_dir)

# CSV Values
na_values = ["null", "None", "nan", "未知", "暂无数据"]

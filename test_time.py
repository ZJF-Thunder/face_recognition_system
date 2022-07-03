import time
#print(time.localtime())
#把time.localtime()初始化成"2022年6月29日 15:01:09"
time_str=time.localtime()
#time.strftime时间格式化不能接中文
print(time.strftime("%Y{}%m{}%d{} %H:%M:%S",time_str).format("年","月","日"))
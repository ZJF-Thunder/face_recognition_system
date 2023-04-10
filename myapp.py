# 导包中的Flask相当于平台
from itertools import chain
import cv2 as cv
from flask import Flask, render_template, request
# 导入base64
import base64
# 导入json模块，为前端传输base64编码数据
import json
# 导入Pillow模块的Image类，帮助我们把ndarray转成图片
from PIL import Image
# 导入人脸识别模块
from face_recognition import load_image_file, face_locations, compare_faces, face_encodings
# 导入detect.py中的main2调用方法
from detect import main
import time
# 返回前端前把数据存到数据库中,导入pymysql
import pymysql
import difflib
# 程序的所有进程都要__name__中
app = Flask(__name__, template_folder="my_html", static_folder="my_js")


# 对比两个字符串相似度函数
def get_equal_rate(str1, str2):
    return difflib.SequenceMatcher(None, str1, str2).quick_ratio()


# 现在点餐，外卖小哥找指定地方买餐,通过装饰器限制网址
# app表示的就是应用，route表示路由
# 这里的"/"表示根目录
# @app.route("/")
# def hello():
#     # 返回值,"Hello world"作为文本在网页中显示
#     return "Hello World"


# @app.route("/index")
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/sign_in", methods=["GET", "POST"])
def sign_in():
    # base编码格式
    data = request.form.get("face")
    # 把数据保存成图片，前端返回的base64编码数据，后端base64解码
    with open("./images/sign_in.jpg", "wb") as f:
        f.write(base64.b64decode(data))
    # 这里face-recognition、load_image_file也是机器学习完成的， 返回数据是ndarray  400x400x3
    mydata = load_image_file("./images/sign_in.jpg")
    # 用yolov5替换face_locations人脸识别函数
    # 返回人脸坐标和识别类别
    img = "./images/sign_in.jpg"
    myresult = main(img)
    # print(myresult)
    # 如果有人脸信息
    if myresult is not None:
        x1, y1, x2, y2, names = myresult[0][0], myresult[0][1], myresult[0][2], myresult[0][3], myresult[1]

        # 切分出人脸,并保存成图片 数据类型为ndarray 175x154x3  对角线
        cut_face = mydata[y1:y2, x1:x2, :]
        # ndarray转图片需要pillow
        myimg = Image.fromarray(cut_face)
        myimg.save("./images/sign_in_id.jpg")  # 保存切分出人脸之后得照片
        # img也是ndayyay类型，也是175x154x3，但是和cut_face在颜色通道上有一些区别，可能和我用的不同函数转化的有关系，所以cut_face不能直接用
        img = cv.imread("./images/sign_in_id.jpg")
        # 保存写有类别名称的人脸图片
        cv.putText(img=img, text=names, org=(5, 50), fontFace=cv.FONT_HERSHEY_SIMPLEX, fontScale=1, color=[0, 0, 255],
                   thickness=None, lineType=cv.LINE_AA)
        cv.imwrite("./images/sign_in_id_label.jpg", img)

        # 把图片数据回传给前端，前端接收的是base64数据，现在cut_face（现在是img）是ndarray类型
        # 通过分析可以知道 b.jpg编译成base64编码，再往前端发送.
        with open("./images/sign_in_id_label.jpg", "rb") as f:
            # img_result进行encode编码，将图片数据变成bytes数据
            img_result = base64.b64encode(f.read())
        # 把img_result的编码输出由unicode转成utf8,去掉输出的b 字符串 只有人脸
        img_result = img_result.decode("utf8")

        # 把time.localtime()初始化成"2022年6月29日 15:01:09"
        time_str = time.localtime()
        # time.strftime时间格式化不能接中文,输出格式变成"2022年6月29日 15:20:19"
        time_sgin_in = time.strftime("%Y{}%m{}%d{} %H:%M:%S", time_str).format("年", "月", "日")
        # 连接数据库
        conn = pymysql.connect(host="localhost", port=3306, user="root", password="981201",
                               database="myface_code")
        # 获取数据库的游标
        cursor = conn.cursor()
        # 安全代码，把多余的记录清除掉，只保留最多10条签到记录，
        # delete from faces 删除全部记录
        cursor.execute("SELECT COUNT(*) FROM faces")
        result = cursor.fetchall()
        resultlist = list(chain.from_iterable(result))
        result = resultlist[0]
        # print("数据条数：", result)
        # 如果数据表中数据量大于10条，就清空数据表
        if result > 10:
            cursor.execute("delete from faces")
            # 再执行一遍提交
            conn.commit()
        # 由游标来执行sql语句,存储人脸数据的时候，存的应该是400*400*3
        cursor.execute("insert into faces(id,face,qiandao,qiantui) values(%s,%s,%s,%s)",
                       (1, img_result, time_sgin_in, None))
        # 提交结果是由连接来完成的
        conn.commit()
        # 最后关闭数据库
        conn.close()
        # 直接发送到前端，由前端自行处理base64的前22个字节。
        # 不管是前端发后端，还是后端发前端，都使用json数据
        # json转字符串用json.dumps
        if names == "mask":
            names_result = "识别到口罩"
        else:
            names_result = "识别到没戴口罩,请戴口罩！"
        return json.dumps({"face": img_result, "time": time_sgin_in, "names": names_result}, ensure_ascii=False)
    # 如果没有人脸信息
    else:
        names_result = "无人脸信息"
        return json.dumps({"face": None, "time": None, "names": names_result}, ensure_ascii=False)


@app.route("/sign_out", methods=["GET", "POST"])
def sign_out():
    # data是一个字符串 摄像头返回的图像
    global time_sgin_out, img_result
    data = request.form.get("face")
    # 把数据保存成图片，前端返回的64编码数据，后端base64解码
    with open("./images/sign_out.jpg", "wb") as f:
        f.write(base64.b64decode(data))

    # 因为数据库存储的是base64编码，不需要转成ndarray，也不需要存图片,直接连接数据库
    mydata = load_image_file("./images/sign_out.jpg")
    # 用yolov5替换face_locations人脸识别函数
    # 返回人脸坐标和识别类别
    img = "./images/sign_out.jpg"
    myresult = main(img)
    # 如果有人脸信息
    if myresult is not None:
        x1, y1, x2, y2, names = myresult[0][0], myresult[0][1], myresult[0][2], myresult[0][3], myresult[1]

        # 切分出人脸,并保存成图片
        cut_face = mydata[y1:y2, x1:x2, :]
        # ndarray转图片需要pillow
        myimg = Image.fromarray(cut_face)
        myimg.save("./images/sign_out_id.jpg")  # 保存切分出人脸之后得照片
        img = cv.imread("./images/sign_out_id.jpg")
        cv.putText(img=img, text=names, org=(5, 50), fontFace=cv.FONT_HERSHEY_SIMPLEX, fontScale=1, color=[0, 0, 255],
                   thickness=None, lineType=cv.LINE_AA)
        cv.imwrite("./images/sign_out_id_label.jpg", img)

        # 把图片数据回传给前端，前端接收的是base64数据，现在cut_face是ndarray类型
        # 通过分析可以知道 b.jpg编译成base64编码，再往前端发送.
        with open("./images/sign_out_id_label.jpg", "rb") as f:
            img_result1 = base64.b64encode(f.read())
        # 把img_result的编码输出由unicode转成utf8,去掉输出的b 字符串 只有人脸  签退的人脸
        img_result1 = img_result1.decode("utf8")

        # 连接数据库
        conn = pymysql.connect(host="localhost", port=3306, user="root", password="981201",
                               database="myface_code")
        # 获取游标，把上一步连接的结果conn引入过来
        cursor = conn.cursor()
        # 执行数据库的逻辑

        # 1、把数据里面所有人脸数据全部查出  保存的是完整得人脸,取出来也是完整的人脸
        cursor.execute("select face from faces")
        # 2、数据执行查询时,结果在cursor.fetchall()方法获取结果
        results = cursor.fetchall()
        index = 0
        for result in results:
            # print("数据库长度:", len(results))
            index += 1
            # 因为result结果是元素，元素只能取0元素，又因为有一个b,去掉b使用decode("utf8")
            # print(result[0].decode("utf8"))
            # 把查出的base64编码赋值给一个变量
            # img_result是一个字符串  数据库中的
            img_result = result[0].decode("utf8")
            # 摄像头和数据库中图片进行比对
            rate = get_equal_rate(img_result1, img_result)
            # 如果相似度大于0.9,就认定是同一个人,就签退 同时保证是最后一条数据
            if rate >= 0.85 and index == len(results):
                print("两个人脸的相似度:", rate)
                # 把time.localtime()初始化成"2022年6月29日 15:01:09"
                time_str = time.localtime()
                # time.strftime时间格式化不能接中文,输出格式变成"2022年6月29日 15:20:19"
                time_sgin_out = time.strftime("%Y{}%m{}%d{} %H:%M:%S", time_str).format("年", "月", "日")
                # 更新数据的时候，人脸数据是全部图像，同时img_result是base64编码
                cursor.execute("update faces set qiantui=%s where face=%s", (time_sgin_out, img_result))
                # 数据执行增删改需要commit提交
                conn.commit()
                # 只要成功比对人脸,证明找到该人脸,一般数据库中不同人脸只有一张,所以成功比对就跳出循环
                break

        # #最后关闭数据库
        conn.close()

        if names == "mask":
            names_result = "识别到口罩"
        else:
            names_result = "识别到没戴口罩,请戴口罩!"
        return json.dumps({"face": img_result1, "time": time_sgin_out, "names": names_result}, ensure_ascii=False)
    # 如果没有人脸信息
    else:
        names_result = "无人脸信息"
        return json.dumps({"face": None, "time": None, "names": names_result}, ensure_ascii=False)


# __name__=="__main__"，这句话意思表示__name__只有等于main才执行
if __name__ == "__main__":
    # app.run(port=8090)
    app.run()

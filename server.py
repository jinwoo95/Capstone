# -\*- coding: utf-8 -\*-


from flask import Flask, request, jsonify, session, redirect, render_template, url_for, session
#from flask_wtf.csrf import CSRFProtect
#from forms import RegisterForm, LoginForm
from pymongo import MongoClient
import pandas as pd
import numpy as np
import os 
import requests
import uuid
import time
import base64
import json
import math
from statistics import mean
from datetime import datetime


app = Flask(__name__)
app.secret_key = b'aaa!111/'
dat = pd.read_csv('food_DB.csv',encoding = 'utf-8')

food_recommend_quantity = pd.read_excel("food_recommend_quantity.xlsx")
food_recommend_quantity = food_recommend_quantity.fillna(0)

# "음식"을 대상으로 추출
dat_cond = (dat.DB군 == "음식")

dat = dat.loc[dat_cond, ]

# reindex
dat = dat.reset_index()


# 필요한 열만 추출
n_columns = ['NO',
            'SAMPLE_ID',
            '식품코드',
            '식품명',
            '식품상세분류',
            '지역 / 제조사',
            '비타민 B2(㎎)',
            '비타민 C(㎎)',
            '총당류(g)',
            '콜레스테롤(㎎)',
            '수분(g)',
            '총 식이섬유(g)',
            '칼슘(㎎)',
            '철(㎍)',
            '나트륨(㎎)',
            '탄수화물(g)',
            '단백질(g)',
            '지방(g)',
            '에너지(㎉)'
           ]
# 필요한 열에 대한 전체 데이터
dat = dat[n_columns]

# 영양성분에 한해서 다시 필터링
n_dat = dat[['비타민 B2(㎎)',
            '비타민 C(㎎)',
            '총당류(g)',
            '콜레스테롤(㎎)',
            '수분(g)',
            '총 식이섬유(g)',
            '칼슘(㎎)',
            '철(㎍)',
            '나트륨(㎎)',
            '탄수화물(g)',
            '단백질(g)',
            '지방(g)',
            '에너지(㎉)'
           ]]


##---------------------------------DB----------------------------------------
##--------------회원가입, 로그인------------------
##user회원가입// user는 dictionary형태여야한다.
def user_join(user) :
    client = MongoClient('localhost', 27017) 
    db = client.testdb.USERINFO
    db.insert_one(user)

#회원가입 유효성 검사(중복 아이디 검사)
def user_join_auth(email) :
    client = MongoClient('localhost', 27017) 
    db = client.testdb.USERINFO
    result = db.find_one({'email' : email})
    return result

##login 검사 유효성 검사.
def user_login(email, password):
    client = MongoClient('localhost', 27017)
    db = client.testdb.USERINFO
    result = db.find_one({'email' : email , 'password' : password})
    return result

#-----------------식단 입력을 위한 것.------------------
##식단 데이터 입력
def insert_user_food(food):
    client = MongoClient('localhost', 27017) 
    db = client.testdb.USER_FOOD 
    db.insert_one(food)

##---------------직접 검색 데이터 db에서 찾기-------------
def food_searchdb(keyword):
    client = MongoClient('localhost', 27017) 
    db = client.testdb.FOOD_NUTRITION_DB
    result = {'food' : keyword}
    temp = db.find_one({'description' : keyword})
    result.update(temp)
    return result

###-------------직접검색에서 즐겨찾기에 음식 등록.-------------
def food_favoritesdb(email,foodInfo):
    client = MongoClient('localhost', 27017) 
    db = client.testdb.USERINFO
    user_info = db.find_one({'email' : email})
    number = len(user_info['favorites'])
    if(number == 0) :
        newvalues =  {"$set" : {'favorites' : [foodInfo]}}
    else :
        user_info['favorites'].append(foodInfo)
        newvalues =  {"$set" : {'favorites' : user_info['favorites']}}  
    db.update_one({'email' : user_info['email']},newvalues)

###-------------즐겨찾기 음식 읽어오기.-------------
def read_favoritesdb(email):
    client = MongoClient('localhost', 27017) 
    db = client.testdb.USERINFO
    user_info = db.find_one({'email' : email})
    number = len(user_info['favorites'])
    if(number == 0) :
        return 0
    else :
        result = user_info['favorites']
        return result
         

#사용자 하루 권장 섭취량 추출하기
def userNutrition(email):
    client = MongoClient('localhost', 27017)
    db = client.testdb.USERINFO
    result = db.find_one({'email' : email})
    return result

##먹었던 식단 정보 find하기(식단 통계를 위한 것)
def findUserfood(email,date):
    client = MongoClient('localhost', 27017)
    db = client.testdb.USER_FOOD
    result = list(db.find({'email' : email,'date' : date}))
    return result



###----------------------------REST API 관련----------------------------------------------------------------------
#메인 페이지.
@app.route('/',methods = ['GET'])
@app.route('/main', methods = ['GET'])
def Home():
    #if (session['logged_in'] == True):
    return render_template('index_Home.html')


#회원가입 유효성 검사 test
    
#---------------------------User 로그인, 회원가입--------------------------------------------------
@app.route('/register', methods = ['GET','POST'])
def register():
    if(request.method == 'GET'):
        return render_template('register.html')
    else : 
        email = request.form.get('useremail') 
        auth = user_join_auth(email)
        print(auth)
        if(auth is not None) :
            return "<script type='text/javascript'>alert('중복된 email 입니다.');history.back()</script>"
        else :
            name = request.form.get('username')
            password = request.form.get('password')
            re_password = request.form.get('re_password')
            age = request.form.get('age')
            height = request.form.get('height')
            weight = request.form.get('weight')
            allergy = request.form.get('allergy')
            sex = request.form.get('sex')
            activity = request.form.get('activity')
            pregnent = request.form.get('pregnant')
            favorites = []
            if not (email and name and password and re_password and age and height and weight and allergy) :
                return "<script type='text/javascript'>alert('모두 입력해주세요');history.back()</script>"
            elif password != re_password:
                return "<script type='text/javascript'>alert('비밀번호가 일치하지 않습니다.');history.back()</script>"
            else: #모두 입력이 정상적으로 되었다면 밑에명령실행(DB에 입력됨)
                info = {'email'  : email, 'name' : name, 'password' : password, 're_password' : re_password, 'height' : height,'weight': weight, 'allergy' : allergy, 'sex' : sex,
                    'activity' : activity ,'pregnent' : pregnent ,'favorites' : favorites}
                k = Calculate_FoodRecommendedQuantity(food_recommend_quantity = food_recommend_quantity, height= int(height), weight = int(weight), age = int(age), sex = sex, isPregnant = pregnent, activity = activity)
                info.update(k)
                user_join(info) 
                return  "<script type='text/javascript'>alert('가입이 완료되었습니다.');location.href = '/login';</script>"  
        return redirect('/')

@app.route('/login', methods = ['GET','POST'])
def login():
    if(request.method == 'POST'):
        email = request.form.get('useremail')
        password = request.form.get('password')
        try :
            result = user_login(email, password)
            session['logged_in'] = True
            session['email'] = email
            return "<script type='text/javascript'>alert('로그인이 완료되었습니다.');location.href = '/';</script>"
        except :
            return "<script type='text/javascript'>alert('로그인 실패');history.back();</script>"
    else :        
        return render_template('login.html') 

@app.route("/logout")
def logout() :
    session['logged_in'] = False
    return render_template('index_Home.html')

#---------------------------음식 입력--------------------------------------------------
#---------------------------직접 검색을 통한 입력-----------------------------------
@app.route('/foodresearch',methods = ['GET','POST'])
def foodresearch():
    if(session['logged_in'] == False):
        return "<script type='text/javascript'>alert('로그인이 필요한 서비스입니다.');location.href = '/main';</script>"
    else:    
        if(request.method == 'GET'):
            return render_template('foodresearch.html')
        else :
            food = request.form.get('food')
            
            food_info = food_searchdb(food)
            
            favorites_check = request.form.get('favorites_check')
            if (food_info is None) :
                return "<script type='text/javascript'>  ; alert('"+food+"란 음식이 없습니다.');history.back();</script>"
            else : 
                food_info = food_processing(food_info)
                date = datetime.today() 
                date = str(date.year) + str(date.month) + str(date.day)
                food_info["date"] = date
                food_info['email'] = session['email']
                insert_user_food(food_info)
                if(favorites_check  == "on" ):
                    temp = food_searchdb(food)
                    temp = food_processing(temp)
                    [temp.pop(key) for key in ["수분(g)",'총당류(g)','총 식이섬유(g)','칼슘(㎎)','철(㎍)','나트륨(㎎)',  '비타민 B2(㎎)','비타민 C(㎎)','콜레스테롤(㎎)']]
                    temp['food'] : food
                    food_favoritesdb(email = session['email'],foodInfo = temp)
                return "<script type='text/javascript'>alert('식단 입력이 완료되었습니다..');location.href = '/main';</script>"

#---------------------------즐겨 찾기를 통한 입력-----------------------------------

@app.route('/favorites',methods = ['GET','POST'])
def favorites():
    if(session['logged_in'] == False):
        return "<script type='text/javascript'>alert('로그인이 필요한 서비스입니다.');location.href = '/main';</script>"
    else :
        if(request.method == 'GET'):
            result = read_favoritesdb(email = session['email'])
            if(result == 0) :
                 return "<script type='text/javascript'>alert('즐겨찾기에 등록된 음식이 없습니다.');location.href = '/main';</script>"
            else :
                number = len(result)
                return render_template('foodfavorites.html',favorites = result, number = number)
        else :
            food = request.form.get("favorites_register_1")
            food = food[:-6]
            food_info = food_searchdb(food)
            food_info = food_processing(food_info)
            date = datetime.today() 
            date = str(date.year) + str(date.month) + str(date.day)
            food_info["date"] = date
            food_info['email'] = session['email']
            insert_user_food(food_info)
            return "<script type='text/javascript'>alert('식단 입력이 완료됐습니다.');location.href = '/main';</script>"
#--------------------------ocr을 통한 입력-----------------------------------
@app.route('/foodocr',methods = ['GET','POST'])
def foodocr():
    if(request.method == 'GET'):
        return render_template('foodocr.html')
    else :
        image = request.files['file']
        result = OCR_NutritionFacts(image)
        result['food'] = 'ocr'
        result['email'] = session['email']
        date = datetime.today() 
        date = str(date.year) + str(date.month) + str(date.day)
        result["date"] = date
        insert_user_food(result)
        return render_template('ocr_result.html',ocr = result)
@app.route('/OCR', methods = ['POST','GET'])
def OCR():
    return "<script type='text/javascript'>alert('식단 입력이 완료됐습니다.');location.href = '/main';</script>"

#---------------------------음식 추천----------------------------------------------------

##추천 알고리즘을 통한 음식 추천 api
@app.route('/recommend', methods = ['GET','POST'])
def recommend():
    if(session['logged_in'] == False):
        return "<script type='text/javascript'>alert('로그인이 필요한 서비스입니다.');location.href = '/main';</script>"
    else :
        date = datetime.today() 
        date_temp = str(date.year) + str(date.month) + str(date.day)
        date_nut =findUserfood(email = session['email'],date = date_temp)
        if(not date_nut) :
            pass
        else:
            for j in range(len(date_nut)):
                [date_nut[j].pop(key) for key in ["_id","food","date","email"]]
                for k in date_nut[j].keys():
                    if(date_nut[j][k] == "-"):
                        date_nut[j][k] = 0 
            for jj in range(1,len(date_nut)):
                for i in date_nut[0].keys():
                    date_nut[0][i] = float(date_nut[0][i]) + float(date_nut[jj][i])
            food = eucFoodRecommend(date_nut[0])
        return render_template('index_Foodrecommend.html',food = food)

##식단 통계 api
@app.route('/statistic',methods = ['GET','POST'])
def statistic():
    if(session['logged_in'] == False):
        return "<script type='text/javascript'>alert('로그인이 필요한 서비스입니다.');location.href = '/main';</script>"
    else :
        if(request.method == 'GET'):
            date = datetime.today() 
            date_ym = str(date.year) + str(date.month)  
            date_d = date.day
            nutrition=[]
            for i in range(1,date_d+1):
                date_temp = str(date.year) + str(date.month) +str(i)
                date_nut =findUserfood(email = session['email'],date = date_temp)
                if(not date_nut) :
                    print(session['email'])
                    nutrition.append('N')
                else:
                    kal = []
                    pro = []
                    for j in range(len(date_nut)):
                        kal.append(float(date_nut[j]['에너지(㎉)']))
                        pro.append(float(date_nut[j]['단백질(g)']))
                    kal = sum(kal)
                    pro = sum(pro)
                    stand_kal = userNutrition(session['email'])['에너지']
                    stand_pro = userNutrition(session['email'])['단백질']
                    stand = {'stand_kal' : stand_kal, 'stand_pro' : stand_pro}
                    user = {'user_kal' : kal , 'user_pro' : pro}
                    if(kal >= stand_kal or pro >=  stand_pro) :
                        nutrition.append('N')
                    else :
                        nutrition.append('Y')
            return render_template('index_Foodstatistic_v2.html',nutrition = nutrition, stand = stand, user = user)
        else :
            return render_template('index_Foodstatistic_v2.html')

##식단 팝업 api
@app.route('/popupN',methods = ['GET','POST'])
def popupN():
    if(session['logged_in'] == False):
        return "<script type='text/javascript'>alert('로그인이 필요한 서비스입니다.');location.href = '/main';</script>"
    else :
        return render_template('pop_up_N.html')

##식단 팝업 api
@app.route('/popupY',methods = ['GET','POST'])
def popupY():
    if(session['logged_in'] == False):
        return "<script type='text/javascript'>alert('로그인이 필요한 서비스입니다.');location.href = '/main';</script>"
    else :
        return render_template('pop_up_Y.html')

##----------------------------------------------일반 함수-------------------------------
def food_processing(result):
        result["에너지(㎉)"] = result.pop("level")
        result["지방(g)"] = result.pop("instruction")
        result["단백질(g)"] = result.pop("sauce")
        result["수분(g)"] = result.pop("ingredient")
        result["탄수화물(g)"] = result["null"][0]
        result["총당류(g)"] = result["null"][1]
        result["총 식이섬유(g)"] = result["null"][2]
        result["칼슘(㎎)"]=result["null"][3]
        result["철(㎍)"] = result["null"][4]
        result["나트륨(㎎)"] = result["null"][5]
        result["비타민 B2(㎎)"] = result["null"][6]
        result["비타민 C(㎎)"] = result["null"][7]
        result["콜레스테롤(㎎)"] =  result["null"][8]
        [result.pop(key) for key in ["_id","title","null","Unnamed: 0","amount","description","time"]]
        return result

# 유클리디안 거리 함수
def euc_dist_func(x,y):   
    return np.sqrt(np.sum((x-y)**2))

def eucFoodRecommend(userInfo):
    for k, v in userInfo.items():
        if(userInfo[k] == "-"):
            userInfo[k] = 0
        else :
            userInfo[k] = float(v)
    # 일일 최소 권장 섭취량 예시
    r_vitamin_B = 1.4  # 리보플라빈
    r_vitamin_C = 100
    r_sugar = 50
    r_cholesterol = 300
    r_water = 1500
    r_fiber = 25        # 식이섬유
    r_calcium = 700
    r_iron = 10         # 철  (임신부의 경우, 24mg)
    r_sodium = 2000       # 나트륨
    r_carbo = 300         # 탄수화물
    r_protein = 80
    r_fat = 34
    r_calories = 2200
    
    # 사용자가 부족한 영양소 (위 두개 변수의 차이)
    d_vitamin_B = r_vitamin_B - userInfo['비타민 B2(㎎)']  # 리보플라빈
    d_vitamin_C = r_vitamin_C - userInfo['비타민 C(㎎)']
    d_sugar = r_sugar - userInfo['총당류(g)']
    d_cholesterol = r_cholesterol - userInfo['콜레스테롤(㎎)']
    d_water = r_water - userInfo['수분(g)']
    d_fiber = r_fiber - userInfo['총 식이섬유(g)']
    d_calcium = r_calcium - userInfo['칼슘(㎎)']
    d_iron = r_iron - userInfo['철(㎍)']        # 철  (임신부의 경우, 24mg)
    d_sodium = r_sodium - userInfo['나트륨(㎎)']       # 나트륨
    d_carbo = r_carbo - userInfo['탄수화물(g)']         # 탄수화물
    d_protein = r_protein - userInfo['단백질(g)']
    d_fat = r_fat - userInfo['지방(g)'] 
    d_calories = r_calories - userInfo['에너지(㎉)']
    
    user = np.array((d_vitamin_B,
                 d_vitamin_C,
                 d_sugar,
                 d_cholesterol,
                 d_water,
                 d_fiber,
                 d_calcium,
                 d_iron,
                 d_sodium,
                 d_carbo,
                 d_protein,
                 d_fat,
                 d_calories))
    
    euc_dist_list = []

    for i in range(len(n_dat)):
        euc_dist = euc_dist_func(user,np.array(n_dat.loc[i, ]))
        euc_dist_list.append(euc_dist)

    min_euc_dist = min(euc_dist_list)
    min_euc_dist_idx = euc_dist_list.index(min_euc_dist)
    
    return dat['식품명'].iloc[min_euc_dist_idx, ]

#OCR 함수정의
def OCR_NutritionFacts(image_file): 
    
    api_url = 'https://506287f2b6b54a93979110cd984c4f3d.apigw.ntruss.com/custom/v1/2411/97429b9bdefb9d13a34503ec00b27aa232cb65255e8ff4c283230b99982f56ec/general'
    secret_key = 'cVJraGF5RXRubHlsR0Zpa1dqU1ViTHBxeW1CaFBCbWY='
    
    file_data = image_file.read()

    request_json = {
        'images': [
            {
                'format': 'png',
                'name': 'demo',
                'data': base64.b64encode(file_data).decode()
            }
        ],
        'requestId': str(uuid.uuid4()),
        'version': 'V2',
        'timestamp': int(round(time.time() * 1000))
    }

    payload = json.dumps(request_json).encode('UTF-8')
    headers = {
      'X-OCR-SECRET': secret_key,
      'Content-Type': 'application/json'
    }

    rawResponse = requests.request("POST", api_url, headers=headers, data = payload)
    response = json.loads(rawResponse.text)
    print(response.get("images")[0].get("message"))
    
    outputs = response['images'][0]['fields']
    units = ['kcal', 'g']
    nutrition_dict = {}
    
    for num in range(len(outputs)):
        for unit in units:
            if unit in outputs[num]['inferText']:
                
                if ")" in outputs[num]['inferText']:
                    continue
        
                try:
                    if int(outputs[num-1]['inferText'].replace(",", "")):
                        if unit == 'kcal':
                            nutrition_dict['열량'] = outputs[num-1]['inferText'] + outputs[num]['inferText']
                    else:
                        nutrition_dict[outputs[num-2]['inferText']] = outputs[num-1]['inferText'] + outputs[num]['inferText']
                    
                except:
                    nutrition_dict[outputs[num-1]['inferText']] = outputs[num]['inferText']
    
    return nutrition_dict 

def stdFoodRecommend(userInfo,n_dat = n_dat, dat = dat):
    for k, v in userInfo.items():
        if(userInfo[k] == "-"):
            userInfo[k] = 0
        else :
            userInfo[k] = float(v)

    # 일일 최소 권장 섭취량 예시
    r_vitamin_B = 1.4  # 리보플라빈
    r_vitamin_C = 100
    r_sugar = 50
    r_cholesterol = 300
    r_water = 1500
    r_fiber = 25        # 식이섬유
    r_calcium = 700
    r_iron = 10         # 철  (임신부의 경우, 24mg)
    r_sodium = 2000       # 나트륨
    r_carbo = 300         # 탄수화물
    r_protein = 80
    r_fat = 34
    r_calories = 2200
    
    # 사용자가 부족한 영양소 (위 두개 변수의 차이)
    d_vitamin_B = r_vitamin_B - userInfo['비타민 B2(㎎)']  # 리보플라빈
    d_vitamin_C = r_vitamin_C - userInfo['비타민 C(㎎)']
    d_sugar = r_sugar - userInfo['총당류(g)']
    d_cholesterol = r_cholesterol - userInfo['콜레스테롤(㎎)']
    d_water = r_water - userInfo['수분(g)']
    d_fiber = r_fiber - userInfo['총 식이섬유(g)']
    d_calcium = r_calcium - userInfo['칼슘(㎎)']
    d_iron = r_iron - userInfo['철(㎍)']        # 철  (임신부의 경우, 24mg)
    d_sodium = r_sodium - userInfo['나트륨(㎎)']       # 나트륨
    d_carbo = r_carbo - userInfo['탄수화물(g)']         # 탄수화물
    d_protein = r_protein - userInfo['단백질(g)']
    d_fat = r_fat - userInfo['지방(g)'] 
    d_calories = r_calories - userInfo['에너지(㎉)']
    
    # userInfo에 대해 dataframe 생성
    user_df = pd.DataFrame([{'비타민 B2(㎎)': d_vitamin_B,
                            '비타민 C(㎎)': d_vitamin_C,
                            '총당류(g)': d_sugar,
                            '콜레스테롤(㎎)': d_cholesterol,
                            '수분(g)': d_water,
                            '총 식이섬유(g)': d_fiber,
                            '칼슘(㎎)': d_calcium,
                            '철(㎍)': d_iron,
                            '나트륨(㎎)': d_sodium,
                            '탄수화물(g)': d_carbo,
                            '단백질(g)': d_protein,
                            '지방(g)': d_fat,
                            '에너지(㎉)': d_calories}])
    
    # 표준화 작업! (유저 데이터와 식품영양DB에 대해)
    user_dat = pd.DataFrame(columns=['비타민 B2(㎎)', '비타민 C(㎎)', '총당류(g)', '콜레스테롤(㎎)', '수분(g)', '총 식이섬유(g)', '칼슘(㎎)', '철(㎍)', '나트륨(㎎)', '탄수화물(g)', '단백질(g)','지방(g)', '에너지(㎉)'])
    std_dat = pd.DataFrame(columns=['비타민 B2(㎎)', '비타민 C(㎎)', '총당류(g)', '콜레스테롤(㎎)', '수분(g)', '총 식이섬유(g)', '칼슘(㎎)', '철(㎍)', '나트륨(㎎)', '탄수화물(g)', '단백질(g)','지방(g)', '에너지(㎉)'])
    
    for c in n_dat.columns:
        m = np.mean(n_dat[c])
        s = np.std(n_dat[c])
        #각각의 column에 대해서 z-value 구하기.
        user_z_value = (user_df[c] - m) / s
        z_value = (n_dat[c] - m) / s

        user_z_dat = pd.DataFrame(user_z_value)
        z_dat = pd.DataFrame(z_value)
        
        user_dat[[c]] = user_z_dat
        std_dat[[c]] = z_dat
    
    std_dist_list = []

    for i in range(len(std_dat)):
        std_dist = euc_dist_func(np.array(user_dat), np.array(std_dat.loc[i, ]))
        std_dist_list.append(std_dist)

    min_std_dist = min(std_dist_list)
    min_std_dist_idx = std_dist_list.index(min_std_dist)


    return dat['식품명'].iloc[min_std_dist_idx, ]

#영양성분 도출
def Calculate_FoodRecommendedQuantity(food_recommend_quantity, height, weight, age, sex, isPregnant, activity):  
    male_index = food_recommend_quantity[food_recommend_quantity['성별 '] == '남자'].index
    female_index = food_recommend_quantity[food_recommend_quantity['성별 '] == '여자'].index
    
    target_nutrient = {}
    
    if sex == '남':     
        for index in male_index:
            if '이상' in food_recommend_quantity['연령'][index]:
                if int(food_recommend_quantity['연령'][index].split(" ")[0]) <= age:
                    target_index = index 
                    target_nutrient = food_recommend_quantity.iloc[target_index][2:].to_dict()
            elif (int(food_recommend_quantity['연령'][index].split("~")[0]) <= age) & (age < int(food_recommend_quantity['연령'][index].split("~")[-1])):
                target_index = index 
                target_nutrient = food_recommend_quantity.iloc[target_index][2:]
        target_nutrient['에너지'] = height*0.01*22*35
    else:   
        for index in female_index:
            if '이상' in food_recommend_quantity['연령'][index]:
                if int(food_recommend_quantity['연령'][index].split(" ")[0]) <= age:
                    target_index = index 
                    target_nutrient = food_recommend_quantity.iloc[target_index][2:].to_dict()
            elif (int(food_recommend_quantity['연령'][index].split("~")[0]) <= age) & (age < int(food_recommend_quantity['연령'][index].split("~")[-1])):
                target_index = index 
                if isPregnant == True: 
                    target_nutrient = food_recommend_quantity.iloc[target_index][2:] + food_recommend_quantity.iloc[22][2:] 
                    target_nutrient = target_nutrient.to_dict()
                else:
                    target_nutrient = food_recommend_quantity.iloc[target_index][2:]
                              
        target_nutrient['에너지'] = height*0.01*21*35
                
    return target_nutrient
if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
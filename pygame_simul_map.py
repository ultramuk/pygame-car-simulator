#!/usr/bin/env python
#-- coding:utf-8 --

import os, rospy
import pygame
import numpy as np
from math import radians, copysign
from std_msgs.msg import Int32MultiArray

class Map(pygame.sprite.Sprite):
    #생성자함수
    def __init__(self, screen, w, h):
        super(Map, self).__init__()
        #지도의 가로, 세로 
        self.width = w
        self.height = h
        self.screen = screen
	#지도 이미지 불러오기
        #convert_alpha()를 통해 RGB 채널을 RGBA 채널로 전환한다. 
        self.image = pygame.image.load("map.png").convert_alpha()
	#Mask 충돌체크를 위한 mask 생성
        self.rect = self.image.get_rect()
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.mask = pygame.mask.from_surface(self.image)
    
    #Map 업데이트 함수
    def update(self):
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.mask = pygame.mask.from_surface(self.image)
	#이미지를 (0,0)에 위치하도록 출력된다.
        self.screen.blit(self.image, (0, 0))

#자동차 클래스
class Car(pygame.sprite.Sprite):
    #생성자함수
    def __init__(self, x, y, screen, angle=0.0, max_steering=30, max_acceleration=1000.0):
        super(Car, self).__init__()
        self.screen = screen
        
	#차량의 현재 위치
        self.x = x
        self.y = y

	#yaw 값 (차량의 진행방향 == 각도)
        self.yaw = angle

	#최대 가속도 값
        self.max_acceleration = max_acceleration
	#최대 조향각 값
        self.max_steering = max_steering
	#브레이크로 인한 감속 가속도 값 (스페이스바를 누르는 경우 사용됨)
        self.brake_deceleration = 100
	#정지마찰력으로 인한 감속 가속도값 (키 눌림이 없는 경우 (엑셀에서 발을 뗀 경우) 적용됨)
        self.free_deceleration = 20
	#선형 가속도
        self.linear_accelation = 0.0
	#선속도 
        self.linear_velocity = 30.0
	#최대 속도
        self.max_velocity = 1000
	#조향각
        self.steering_angle = 0.0
        #자동차 휠베이스 (축거 : 앞바퀴축과 뒷바퀴축 사이의 거리)
        self.wheel_base = 84

	#자동차 이미지 좌표 (가로x세로 128x64 픽셀의 자동차 그림파일. car.png)
        self.car_img_x = 0
        self.car_img_y = 0
        self.car_x_ori = [-64,-64, 64, 64] # 왼쪽 위아래, 오른쪽 위아래 포인트 총4개
        self.car_y_ori = [-32, 32,-32, 32] # 왼쪽 위아래, 오른쪽 위아래 포인트 총4개

	#차량 이미지를 불러온다.
    # convert_alpha()를 통해 RGB 채널을 RGBA 채널로 전환한다. 
        self.image = pygame.image.load("car.png").convert_alpha()
	#차량의 변위각만큼 이미지를 회전시킨다. 
        self.rotated = pygame.transform.rotate(self.image, self.yaw)
        self.rect = self.rotated.get_rect()
	#변화한 이미지로 다시 mask를 생성한다. 
        self.mask = pygame.mask.from_surface(self.image)
        
    #차량 업데이트 함수
    def update(self, dt):
 	#선속도를 계산한다. (선속도=선형가속도x단위시간)
        self.linear_velocity += (self.linear_accelation * dt)
	#선속도를 (-100,100) 사이로 값을 제한한다.
        self.linear_velocity = min(max(-self.max_velocity, self.linear_velocity), self.max_velocity)

	#각속도
        self.angular_velocity = 0.0
        
	#조향각이 0이 아니라면
        if self.steering_angle != 0.0:
	    #각속도를 계산한다. 각속도=(선속도/회전반지름)
            self.angular_velocity = (self.linear_velocity / self.wheel_base) * np.tan(np.radians(self.steering_angle))
        
	#각변위를 계산해 angle 값에 더해준다. (각속도x시간=각변위)
        self.yaw += (np.degrees(self.angular_velocity) * dt)
	#이동변위를 계산해 spatium(이동거리) 값에 적용한다. (선속도x시간=이동변위)
        self.spatium = self.linear_velocity * dt
        
	#삼각비를 이용해 x,y 좌표를 구해준다.
        self.x += (self.spatium * np.cos(np.radians(-self.yaw)))
        self.y += (self.spatium * np.sin(np.radians(-self.yaw)))
        
	#자동차 이미지의 새로운 이미지 좌표를 계산하기 위한 리스트를 선언한다. 
        car_x = [0,0,0,0]
        car_y = [0,0,0,0]

	#자동차 이미지의 왼쪽상단, 오른쪽상단, 왼쪽하단, 오른쪽하단의 좌표를 이용해서 자동차가 회전한 변위각에 현재 위치를 더하여 자동차의 이동한 위치를 계산한다. 
        for i in range(4):
            car_x[i] = self.car_x_ori[i] * np.cos(-radians(self.yaw)) - self.car_y_ori[i] * np.sin(-radians(self.yaw)) + self.x
            car_y[i] = self.car_x_ori[i] * np.sin(-radians(self.yaw)) + self.car_y_ori[i] * np.cos(-radians(self.yaw)) + self.y 

	#새로운 이미지 좌표 리스트(x, y 각각)에서 가장 작은 값을 반올림한 후 정수로 변환하여 자동차 이미지의 새로운 좌표를 지정한다.
        self.car_img_x = int(round(min(car_x)))
        self.car_img_y = int(round(min(car_y)))

	#새로 계산된 변위각 만큼 차량 이미지를 회전시킨다. 
        self.rotated = pygame.transform.rotate(self.image, self.yaw)
        self.rect = pygame.Rect(self.car_img_x, self.car_img_y, self.rotated.get_rect().w, self.rotated.get_rect().h)
	#회전 시킨 이미지로 다시 mask를 생성한다. 
        self.mask = pygame.mask.from_surface(self.rotated)
	#회전 시킨 이미지를 새로운 이미지 좌표에 위치하도록 출력한다. 
        self.screen.blit(self.rotated, [self.car_img_x, self.car_img_y])

#ROS 클래스
class Ros:
    #생성자함수
    def __init__(self):
	#"simulator" ros 노드를 만들어준다. 
        rospy.init_node("simulator")
	#"xycar_motor_msg"라는 토픽이 오면 motor_callback을 실행한다. 
        rospy.Subscriber("xycar_motor_msg", Int32MultiArray, self.motor_callback)
        
	#"ultrasonic"라는 토픽을 보내는 publisher 객체를 생성한다. 
        self.us_pub = rospy.Publisher("ultrasonic", Int32MultiArray, queue_size=1)
	#선속도
        self.linear_velocity = 50.0
	#조향각
        self.steering_angle = 0
	#토픽 메시지
        self.us_msg = Int32MultiArray()

    #조향각과 선속도를 설정하는 함수
    def motor_callback(self, data):
        self.steering_angle = data.data[0] 
        self.linear_velocity = data.data[1]

    #초음파 데이터들을 토픽 메시지에 넣어서 publish 하는 함수 
    def pub_ultrasonic(self, no1, no2, no3, no4, no5, no6, no7, no8):
        self.us_msg.data = [no1, no2, no3, no4, no5, no6, no7, no8]
        self.us_pub.publish(self.us_msg)


#게임을 실행하는 클래스(main 클래스)
class Game:
    #생성자함수
    def __init__(self):
	#pygame을 초기화 하는 함수
        pygame.init()
	#windows title을 정하는 함수
        pygame.display.set_caption("Car Simulator")
	#pygame window size 설정
        self.screen_width = 1300  #1307
        self.screen_height = 800 #1469
	#설정된 windows size를 적용하는 함수
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
	#while 루프 반복주기. 화면갱신 FPS를 설정하기 위한 시간객체 생성
        self.clock = pygame.time.Clock()
	#while 루프 반복주기
        self.ticks = 60
	#아래 while 루프를 종료시키기 위해 선언하는 변수
        self.exit = False
	#ROS 객체 생성
        self.ros = Ros()

    #game을 실행하는 함수
    def run(self):
        
	#MAP 객체 생성
        mapped = Map(self.screen, self.screen_width, self.screen_height)
        #Car 객체 생성. 처음 진행방향은 위쪽(90도)으로 설정
        car = Car(200, 700, self.screen, angle=90)
	#첫번째 충돌을 무시하기 위한 변수
        first_frame = False

        while not self.exit:
	    #단위시간의 크기 설정 - 단위시간이란 1 frame이 지나가는데 걸리는 시간이다.
            #해당 시간이 있어야 속력=거리/시간 등의 공식을 계산할 수 있다.
            dt = float(self.clock.get_time()) / 1000.0

	    #이벤트 감지. 여기선 종료이벤트만 확인하여 루프 종료변수를 True로 변경
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.exit = True

	    #자동차의 조향각과 선속도를 ros로부터 받아온 데이터로 설정
            car.steering_angle = -self.ros.steering_angle * float(float(3.0)/float(5.0))
            car.linear_velocity = self.ros.linear_velocity
	    #선가속도
            car.linear_accelation = 0.0
            
	    #선가속도의 범위를 (-1000.0~1000.0)사이의 값으로 제한한다.
            car.linear_accelation = max(-car.max_acceleration, min(car.linear_accelation, car.max_acceleration))
	    #steering의 범위를 (-30~30)사이의 값으로 제한한다.
            car.steering_angle = max(-car.max_steering, min(car.steering_angle, car.max_steering))

	    # 거리센서 8개의 거리정보를 모아서 ultrasonic 토픽에 담아 발행한다
            self.ros.pub_ultrasonic(10, 20, 30, 40, 50, 60, 70, 80)

	    #만약 지도와 차량 이미지가 충돌한다면,
            if pygame.sprite.collide_mask(mapped, car) != None:
		#while 루프를 종료시키기 위해 True로 선언
                self.exit = True
                if first_frame == False:
                    first_frame = True
                    self.exit = False

	    #windows 화면을 흰색으로 칠한다. 
            self.screen.fill((255, 255, 255))
            
	    #변화된 수치를 적용한다.  
            mapped.update()
            car.update(dt)

            pygame.display.update()
	    #게임 프레임을 지정 (60fps)
            self.clock.tick(self.ticks)
            
        pygame.quit()

if __name__ == '__main__':
    game = Game()
    game.run()

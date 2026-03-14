local app部分安排几个存储的list
1.短距聊天list
BLE_find list  存储所有扫描到的蓝牙模块，并保持一定更新频率
heartbeat_receive list  接收别的用户发来的heart beat，并保持一定的更新频率，

> 补充，heartbeat机制：处理A单向扫描到B，B没有单项扫描到A的情况。A会给所有BLE_find list的对象通过message通道发送heartbeat类型的消息，频率目前为1hz左右，对方接收到之后，用于维护heartbeat_receive_list的状态，最终让B把A也计算在chatable list中

chatable list：对BLE_find list和heartbeat_receive list 做相加操作，取得chatable list，实时更新


2.好友机制
friend list  接受对方申请，并同意；或发送对方申请，并被对方接受之后，添加对方进入friend list

3.拉黑机制
block list 将对方单方向拉黑后进入block list

4.用户信息存储机制
会对所有涉及到的用户申请并存储其个人信息，包括user_id、profile、头像、是否在匿名状态、昵称等，保持一定的更新频率


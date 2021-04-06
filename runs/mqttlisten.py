import paho.mqtt.client as mqtt

mqtt_broker_ip = "openwb.garnix.de"


def getserial():
   # Extract serial from cpuinfo file
   with open('/proc/cpuinfo', 'r') as f:
      for line in f:
         if line[0:6] == 'Serial':
            return line[10:26]
      return "0000000000000000"


def on_connect(client, userdata, flags, rc):
   # subscribe to all set topics
   # client.subscribe("openWB/#", 2)
   # client.subscribe("openWB/graph/#", 2)
   # client.subscribe("openWB/set/#", 2)
   client.subscribe("openWB/config/#", 2)
   print("Subscribed.")


# handle each set topic
def on_message(client, userdata, msg):
   print("Message for you! Topic %s payload %s" % (msg.topic, msg.payload.decode()))


client = mqtt.Client("openWB-mqttsub-" + getserial())
client.on_connect = on_connect
client.on_message = on_message

client.connect(mqtt_broker_ip, 1883)
client.loop_forever()
client.disconnect()

import paho.mqtt.client as mqtt

# MUST MATCH the topic in index.html
TOPIC = "my_unique_project_channel_12345/control"

def on_connect(client, userdata, flags, rc, properties=None):
    print("Connected to EMQX Broker!")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8")
    print(f"Received signal: {payload}")
    
    if payload == "ON":
        print(">>> STATUS: ON - Executing Python local script! <<<")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

# Connect to EMQX broker on standard MQTT port 1883
client.connect("broker.emqx.io", 1883, 60)

print("Listening for triggers on EMQX... Press Ctrl+C to exit.")
client.loop_forever()
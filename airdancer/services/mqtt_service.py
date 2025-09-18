"""MQTT service implementation"""

import json
import logging

import paho.mqtt.client as mqtt

from .interfaces import MQTTServiceInterface, DatabaseServiceInterface
from ..config.settings import MQTTConfig

logger = logging.getLogger(__name__)


class MQTTService(MQTTServiceInterface):
    """Service for MQTT operations"""

    def __init__(self, database_service: DatabaseServiceInterface, config: MQTTConfig):
        self.database_service = database_service
        self.config = config
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.discovered_switches: set[str] = set()

        # Configure authentication
        if self.config.username:
            self.client.username_pw_set(self.config.username, self.config.password)

        # Configure TLS
        if self.config.use_tls:
            self.client.tls_set()

    def start(self) -> None:
        """Start the MQTT client"""
        protocol = "mqtts" if self.config.use_tls else "mqtt"
        logger.info(
            f"Attempting to connect to MQTT broker at {protocol}://{self.config.host}:{self.config.port}"
        )

        if self.config.use_tls:
            logger.info("Using TLS/SSL encryption")
        if self.config.username:
            logger.info(
                f"Using MQTT authentication with username: {self.config.username}"
            )

        try:
            self.client.connect(self.config.host, self.config.port, 60)
            self.client.loop_start()
            logger.info(
                f"Successfully connected to MQTT broker at {protocol}://{self.config.host}:{self.config.port}"
            )
        except Exception as e:
            logger.error(
                f"Failed to connect to MQTT broker at {protocol}://{self.config.host}:{self.config.port}: {e}"
            )

    def stop(self) -> None:
        """Stop the MQTT client"""
        self.client.loop_stop()
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        """Handle MQTT connection"""
        if reason_code == 0:
            logger.info("MQTT client successfully connected to broker")
            logger.info("Subscribing to Tasmota discovery topic: tasmota/discovery/#")
            client.subscribe("tasmota/discovery/#")
            logger.info("Subscribing to switch LWT topics: tele/+/LWT")
            client.subscribe("tele/+/LWT")
            logger.info("Subscribing to switch power state topics: stat/+/POWER")
            client.subscribe("stat/+/POWER")
            logger.info("MQTT subscriptions completed, ready to discover switches")

            # Query power state for any switches with unknown state
            self.query_unknown_power_states()
        else:
            logger.error(f"MQTT connection failed with reason code: {reason_code}")

    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = msg.payload.decode()

            if topic.startswith("tasmota/discovery/"):
                self.handle_discovery(payload)
            elif topic.endswith("/LWT"):
                switch_id = topic.split("/")[1]
                status = "online" if payload == "Online" else "offline"
                self.database_service.update_switch_status(switch_id, status)
                logger.info(f"Switch {switch_id} is now {status}")
            elif topic.startswith("stat/") and topic.endswith("/POWER"):
                switch_id = topic.split("/")[1]
                power_state = payload.upper()  # Should be "ON" or "OFF"
                self.database_service.update_switch_power_state(switch_id, power_state)
                logger.info(f"Switch {switch_id} power state: {power_state}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def handle_discovery(self, payload: str):
        """Handle Tasmota discovery messages"""
        try:
            logger.debug(f"Processing discovery message: {payload}")
            data = json.loads(payload)
            switch_id = data.get("t")

            if not switch_id:
                logger.warning(f"Received discovery message with no switch id: {json.dumps(data)}")
                return

            device_info = {
                "ip": data.get("ip"),
                "hostname": data.get("hn"),
                "mac": data.get("mac"),
                "model": data.get("md"),
                "software": data.get("sw"),
            }

            if switch_id not in self.discovered_switches:
                self.discovered_switches.add(switch_id)
                self.database_service.add_switch(switch_id, json.dumps(device_info))
                logger.info(f"🔌 Discovered new Tasmota switch: {switch_id}")
                logger.info(f"   └─ IP: {device_info.get('ip', 'unknown')}")
                logger.info(f"   └─ Model: {device_info.get('model', 'unknown')}")
                logger.info(f"   └─ Hostname: {device_info.get('hostname', 'unknown')}")
                logger.info(f"   └─ MAC: {device_info.get('mac', 'unknown')}")
                logger.info(f"   └─ Software: {device_info.get('software', 'unknown')}")

                # Query power state for newly discovered switch
                logger.info(f"   └─ Querying power state for {switch_id}")
                self.query_power_state(switch_id)
            elif switch_id:
                # Switch already discovered, check for updates
                existing_switch = self.database_service.get_switch(switch_id)
                if existing_switch:
                    new_device_info = device_info

                    # Compare with existing device info
                    try:
                        old_device_info = (
                            json.loads(existing_switch.device_info)
                            if existing_switch.device_info
                            else {}
                        )
                    except (json.JSONDecodeError, TypeError):
                        old_device_info = {}

                    changes = []
                    for key, new_value in new_device_info.items():
                        old_value = old_device_info.get(key)
                        if old_value != new_value:
                            changes.append(f"{key}: {old_value} → {new_value}")

                    if changes:
                        # Update the switch with new device info
                        self.database_service.add_switch(
                            switch_id, json.dumps(new_device_info)
                        )
                        logger.info(f"🔄 Updated Tasmota switch: {switch_id}")
                        for change in changes:
                            logger.info(f"   └─ {change}")
                    else:
                        logger.debug(f"Switch {switch_id} rediscovered with no changes")
        except Exception as e:
            logger.error(f"Error handling discovery message: {e}")
            logger.error(f"Problematic payload: {payload}")

    def send_command(self, switch_id: str, command: str, value: str = "") -> bool:
        """Send a command to a switch"""
        topic = f"cmnd/{switch_id}/{command}"
        try:
            self.client.publish(topic, value)
            logger.info(
                f"Sent command {command} with value '{value}' to switch {switch_id}"
            )
            return True
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False

    def bother_switch(self, switch_id: str, duration: int = 15) -> bool:
        """Activate switch for specified duration"""
        # Use TimedPower1 to turn on for specified duration
        return self.send_command(
            switch_id,
            "TimedPower1",
            str(duration * 1000),  # Convert to milliseconds
        )

    def switch_on(self, switch_id: str) -> bool:
        """Turn switch on"""
        return self.send_command(switch_id, "Power1", "ON")

    def switch_off(self, switch_id: str) -> bool:
        """Turn switch off"""
        return self.send_command(switch_id, "Power1", "OFF")

    def switch_toggle(self, switch_id: str) -> bool:
        """Toggle switch state"""
        return self.send_command(switch_id, "Power1", "TOGGLE")

    def query_power_state(self, switch_id: str) -> bool:
        """Query current power state of switch"""
        return self.send_command(switch_id, "Power", "")

    def query_unknown_power_states(self):
        """Query power state for all switches with unknown power state"""
        switches = self.database_service.get_all_switches()
        unknown_switches = [s for s in switches if s.power_state == "unknown"]

        if unknown_switches:
            logger.info(
                f"Querying power state for {len(unknown_switches)} switches with unknown state"
            )
            for switch in unknown_switches:
                logger.info(f"   └─ Querying power state for {switch.switch_id}")
                self.query_power_state(switch.switch_id)

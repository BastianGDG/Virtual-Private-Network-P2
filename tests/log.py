import logging

IP = "192.168.0.10"
ID = "03"
Key = "123123112"

logging.basicConfig(
    filename="errors.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.debug("Key is %s", Key)     # laveste
logging.info("VPN is running on %s", IP)
logging.warning("Latency is 200 ms on user ID %s", ID)
logging.error("User %s unexpectely disconnected", ID)
logging.critical("Can't reach server on %s", IP)  # højeste

from .responses import OpsWorksResponse

# AWS OpsWorks has a single endpoint: opsworks.ap-south-1.amazonaws.com
# and only supports HTTPS requests.
url_bases = [r"https?://opsworks\.ap-south-1\.amazonaws.com"]

url_paths = {"{0}/$": OpsWorksResponse.dispatch}

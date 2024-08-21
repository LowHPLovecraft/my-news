import pathlib as pa
import certifi

certifi_pems_path = pa.Path(certifi.where())

for crt_path in pa.Path(__file__).parent.glob('*.crt'):
    print(f'Processing `{crt_path.name}`')
    certifi_pems = certifi_pems_path.read_text()
    crt = crt_path.read_text()
    if crt not in certifi_pems:
        certifi_pems_path.write_text(f"{certifi_pems}\n{crt}")
    else:
        print(f"`{crt_path.name}` is already in `{certifi_pems_path}`")

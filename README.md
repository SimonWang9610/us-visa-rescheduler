# visa_rescheduler

US VISA (ais.usvisa-info.com) appointment re-scheduler - Colombian adaptation

## Prerequisites

- Having a US VISA appointment scheduled already
- Firefox browser installed (to be controlled by the script)
- Python v3 installed (for running the script)

## Usage

> must run `pip3 install -r requirements.txt` before running the script

```bash
python3 visa_rescheduler.py --config <config_file_path>
```

see more usage

```bash
python3 visa_rescheduler.py -h
```

## Config

1. json file

```json
{
  "username": "<your_email>",
  "password": "<your password>",
  "schedule_id": "<your schedule id>",
  "country_code": "en-ca",
  "date_before": "<preferred date before, format: yyyy-mm-dd>"
}
```

### find your schedule id:

after login, the url will be like this: `https://ais.usvisa-info.com/en-ca/niv/groups/<scheudle_id>`,
the `<schedule_id>` is the one you need to put in the config file.

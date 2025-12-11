# Eko Region scheduler

> **Purpose**: This repository is a OCR based solution to retrieve data from Eko-region waste schedule file

So you want to create calendar waste schedule reminder, but Eko-Region provides only paper (and online) schedule table, 
that you can't copy but needs to create it by hand? 

This solution is for you. 

This simple program written in python is using OCR power to convert pdf file with waste schedule into *.ics file ready to import to your calendar.

## 🚀 Getting Started

### Docker App

There is a simple web UI application to upload, download or even use search for your schedule and generate *.isc file.

To do so you need to create docker image from Dockerfile

```cmd
docker build -t eko-region-scheduler:latest .
```

To run application run 
```cmd
docker run -p 8501:8501  eko-region-scheduler:latest
```

### Shell script

For those who wants run it locally there is a shell script ready to run (with --help documentation)

First install required packages
```cmd
pip install -r requirements.txt
```

Then you can run it
```cmd
cd src
python3 main.py file --path <path_to_file>
```
As this is OCR and it still can make mistakes, i advise to look into resources/tmp/csv folder after first run and compare *.csv file with input file.
If there is some differences you can correct *.csv file and run below command to proceed with correct data,

```cmd
python3 main.py csv --path <path_to_csv> --year <year_of_schedule>
```


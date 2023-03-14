# Planet Labs image pipeline

Automates selection and acquisition of PlanetLab's satellite imagery. The user provides a .csv file with the parameters to be used in the image query, and the program automatically handles the rest. 

It also leverages the Instituto Hidrográfico's HTML API to also estimate tidal height at time of image capture, allowing image filtering based on tides as well.


## 1. Setup - first time

This program has only been tested in, and all setup steps will be given for Ubuntu 22.04. 

**1. Clone the repo:**  
```
git clone https://github.com/MarcioFCMartins/planet_img_pipeline
```

Then navigate into it:

```
cd ./planet_img_pipeline
```

**2. Create a virtual environment**

```
python3 -m venv ./venv
```

All required packages will be installed in this virtual environment. You need to activate it:

```
source ./venv/bin/activate
```

**3. Install python libraries**
```bash
sudo apt install python3-pip
pip3 install -r requirements.txt
```

## 2. Usage

### 2.1. Prepare requests

**Region of interest:**  
Your regions of interest should provided as geoJSON files. They can be placed anywhere you want, but for ease of use I recommend placing them in `inputs`. 

Currently, the program only handles single polygons. If you place files with any other geometry type or multiple polygons, only the first one will be used.


**Query parameters:**  
Image selection is done based on parameters passed through a `csv` file, which can be found in `inputs/image-queries.csv`.

Currently, the following image parameters can be passed to the program:  
1. roi -  Polygon of the region of interest for which images will be selected.
2. start_date -  Earliest date acceptable.
3. end_date - Latest date acceptable.
4. max_cloud_cover - Maximum cloud coverage allowed in selected images.
5. asset_type - Asset type which will be downloaded ([documentation](https://developers.planet.com/docs/apis/data/items-assets/)). Currently, only `PScene` assets are supported.
6. min_tide - Minimum tidal height acceptable.
7. max-tide  Maximum tidal height acceptable.
8. nearest_port - This is the code for the reference port to be used to estimate tides. These are numeric codes provided by the Instituto Hidrográfico. You can consult a list of available sites at the end of this document .

# TODO: Add port list

### 2.2. Check available images  

After filling out your requests' details, you're ready to check which information is available.

### 2.3. Excluding bad queries

Right now this is just bad. You have to basically delete your download queue and ask for a new set of queries.

### 2.4. Download images

# 3. Goals

1. Add an actual query management system. User should be able to specify queries that he wants to remove from the download queue

# Contribute

If you'd like to contribute to Planet Labs image pipeline, check out https://github.com/MarcioFCMartins/planet_img_pipeline

# Planet Labs image pipeline

Automates selection and acquisition of PlanetLab's satellite imagery. The user provides a .csv file with the parameters to be used in the image query, and the program automatically handles the rest. 

It also leverages the Instituto Hidrográfico's HTML API to also estimate tidal height at time of image capture, allowing image filtering based on tides as well.


## Setup - first time

This program has only been tested in Ubuntu 22.04.

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

<br>
<br>

**4. Planet API key**
### 2.1. Planet API key

To perform any operation using the Planet API, you have to provide your own API key. 

Go to [your planet account page](https://www.planet.com/account). You'll find your key in the "My settings" tab. 

Then, create a text file called `.env` in the repository and add the following content:

```
PLANET_KEY=<your-key-here>
```

You should replace the \<your-key-here\> with your own API key. Do NOT share this with other people.

<br>

## 2 Usage

### 2.1 Prepare queries
**Region of interest:**  
Your regions of interest should provided as geoJSON files.  Currently, the program only handles single polygons. If you place files with any other geometry type or multiple polygons, only the first one will be used.

**Query parameters:**  
Image selection is done based on parameters passed through a `csv` file, which can be found in `inputs/image-queries.csv`.

Currently, the following image parameters can be passed to the program:  
1. roi -  Path to the polygon of the region of interest for which images will be selected.
2. start_date -  Earliest date acceptable (format YYYY-MM-DD).
3. end_date - Latest date acceptable (format YYYY-MM-DD).
4. max_cloud_cover - Maximum cloud coverage allowed in selected images.
5. asset_type - Asset type which will be downloaded ([documentation](https://developers.planet.com/docs/apis/data/items-assets/)). Currently, only `PScene` assets are supported.
6. min_tide - Minimum tidal height acceptable. If you do not want to use tide filtering, leave blank.
7. max-tide  Maximum tidal height acceptable. If you do not want to use tide filtering, leave blank.
8. port - This is the code for the reference port to be used to estimate tides. These are numeric codes provided by the Instituto Hidrográfico. You can consult a list of available sites here below.
9. n_layers - How many overlapping layers you are aiming for in your ROI

**Port list**

| port_id|port_name                  |
|-------:|:--------------------------|
|      12|Leixões                    |
|      13|Aveiro - Molhe Central     |
|      15|Cascais                    |
|      16|Lisboa                     |
|      18|Lagos                      |
|      19|Faro - Olhão               |
|      20|Setúbal - Tróia            |
|      21|Vila Real de Santo António |
|      28|Sesimbra                   |
|      29|Peniche                    |
|      43|Sines                      |
|      73|Figueira da Foz            |
|      74|Viana do Castelo           |
|     112|Funchal                    |
|     211|Ponta Delgada              |
|     221|Angra do Heroísmo          |
|     231|Horta                      |
|     243|Lajes das Flores           |
|     245|Vila do Porto              |
|     311|Porto Grande               |
|     312|Praia                      |
|     335|Palmeira                   |
|     411|Porto do Cacheu            |
|     412|Ilheu do Caió              |
|     413|Porto de Bubaque           |
|     511|Baía de Ana Chaves         |
|     521|Baía de St. António        |
|     611|Soyo                       |
|     612|Luanda                     |
|     613|Lobito                     |
|     614|Namibe                     |
|     711|Maputo                     |
|     712|Inhambane                  |
|     713|Beira                      |
|     714|Chinde                     |
|     715|Quelimane                  |
|     716|Pebane                     |
|     717|Angoche                    |
|     718|Ilha de Moçambique         |
|     719|Pemba                      |
|     721|Mocimboa da Praia          |
|     727|Nacala                     |
|     814|Porto de Macau             |


<br>

### 2.2 Check available images  

After filling out your requests' details, you're ready to check which information is available. You'll do that by running `prepare_download_queues.py`. This file will check your submitted queries, see what images are available that match your criteria, and export reports for each one. A download_queue file is also created, which will be used later to download your desired images.

It requires 3 arguments:  
- queries - Path to CSV file with your queries (see 2.2)
- queue - Path to download_queue file. If you have no previously created file, a new one will be created.
- report - Path of folder to store reports to preview imagery available for each query. These reports include the area usage of the query, thumbnail preview of each available image and some metadata about them. The reports are named according to the following convention: `roi_startdate-enddate_mintide-maxtide`. For example, for a query with a roi file named "ria formosa.geojson", from 2024-01-01 to 2024-01-31 with tides ranging from 0.5 to 1 meter, the following name would be used: `ria formosa_20240101-20240131_0.5-1`

Example: 

```python
python3 ./src/planet_img_pipeline/prepare_download_queues.py --queries ./inputs/image-queries.csv --queue ./outputs/download_queue.json --report ./outputs/reports
```

<br>

### 2.3 Excluding bad queries

At the moment, there is no true functionality to do this. My recommendation is that you delete your download_queue file, then delete your bad queries from the query list, and re-run the previous step.

<br>

### 2.5. Download images

Now that your queries have been analyzed, we can proceed with the download.

The program `download_orders` will deal with that. You must provide it 2 arguments:
- queue - Path to download_queue file
- storage - Folder to save your assets to. Please note that a new folder will be created inside it, with the following naming convention: `roi_startdate-enddate_mintide-maxtide`. For example, for a query with a roi file named "ria formosa.geojson", from 2024-01-01 to 2024-01-31 with tides ranging from 0.5 to 1 meter, the following name would be used: `ria formosa_20240101-20240131_0.5-1`

Example:

```python
python3 ./src/planet_img_pipeline/download_orders.py --queue ./inputs/image-queries.csv --storage /mnt/10274c4b-4f18-41e0-a518-ff86b71a055f/planet_labs_imagery
```

<br>
<br>

# 3. Goals

1. Add an actual query management system. User should be able to specify queries that he wants to remove from the download queue

<br>
<br>



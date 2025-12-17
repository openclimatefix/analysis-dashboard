# uk analysis dashboard

<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-10-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

[![ease of contribution: hard](https://img.shields.io/badge/ease%20of%20contribution:%20hard-bb2629)](https://github.com/openclimatefix#how-easy-is-it-to-get-involved)

Internal dashboard for OCF to track forecast statistics and log the historical data of the forecast performance.

The analysis dashboard is a tool that was developed for OCF’s internal use and continues to evolve.

Built with [Streamlit](https://streamlit.io/), a Python-based framework made specifically for creating data apps, the dashboard tracks and displays Quartz Solar and other data model statistics, such as mean absolute error (MAE), normalized mean absolute error (nMAE) for all the client sites. The database provides the error statistic using comparing the live generation with the forecast provided. Internally it has the option of chosing the forecast horizion to check the performance with genration. The larger the error, the less accurate the forecast.

Thanks to the analysis dashboard, OCF has a valuable feedback tool for understanding the accuracy of the forecasts being provided to it's clients.

## Installation

### **Using uv (Recommended)**

This project uses [uv](https://docs.astral.sh/uv/) for fast and reliable dependency management.

**Prerequisites:**

Install uv if you haven't already:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Steps:**

1. Clone the repository and navigate to the project folder:

```shell
git clone https://github.com/openclimatefix/analysis-dashboard.git
cd analysis-dashboard
```

2. Install dependencies:

```shell
uv sync
```

3. Create a login secret:

```shell
echo 'password = "example"' > src/.streamlit/secrets.toml
```

4. Run the app:

```shell
cd src && uv run streamlit run main.py
```

### **Manual Installation (Legacy)**

You can also install using pip, though uv is recommended for better performance:

In the main project folder, install from pyproject.toml:

```shell
pip install -e .
```

Create a login secret:

```shell
echo 'password = "example"' > src/.streamlit/secrets.toml
```

Run app:

```shell
cd src && streamlit run main.py
```

## Database connection

To run the app locally, you'll need to connect it to the `forecast development database`

OCF team members can connect to the `forecast development database` using [these Notion instructions](https://www.notion.so/openclimatefix/Connecting-to-AWS-RDS-bf35b3fbd61f40df9c974c240e042354). Add `DB_URL= (db_url from notion documents)` to a `secrets.toml` file. Follow the instructions in the Notion document to connect to the database v.

To connect to the database platform, use `DATA_PLATFORM_HOST` and `DATA_PLATFORM_PORT`. 

Run app:

```shell
cd src && uv run streamlit run main.py
```

## Using Docker Compose**

This method uses Docker Compose to set up the app and its environment automatically.

**Prerequisites:**

You need to have Docker and Docker Compose installed on your machine. If you don't have them, you can download them from the [Docker website](https://www.docker.com/get-started).

**Steps:**

1. Clone the repository and navigate to the project folder:

```shell
git clone https://github.com/openclimatefix/analysis-dashboard.git

cd analysis-dashboard
```

2. Create a `.env` file in the root directory and add the following environment variables:

```shell
# DB_URL=your-database-url      # Optional, if not available, you can skip this line
REGION=india                  # Choose 'india' or 'uk'
ENVIRONMENT=development       # or 'production'
password=example              # Set your password here
SHOW_PVNET_GSP_SUM=0          # Set this to 1 if you want to show pvnet_gsp_sum model
```

3. Create a `secrets.toml` file in the `src/.streamlit` directory and add the following line:

```shell
echo 'password = "example"' > src/.streamlit/secrets.toml
```

4. Build the Docker image and start the app:

```shell
docker-compose up --build
```

5. Open your browser and go to `http://localhost:8501` to view the app.

6. To stop the app, press `Ctrl+C` in the terminal, and then run:

```shell
docker-compose down
```

## Files

### main.py

`main.py` contains functions for the `home page` of the app, which focuses on MAE for the OCF `Quartz Solar` forecast.

### main_india.py

`main_india.py` contains functions for the `home page` of the app, which focuses on MAE for the OCF `Quartz Energy` forecast.

### forecast.py

`forecast.py` contains functions for the `forecast page`. The forecast page looks at how well each of OCF's forecast models is performing compared to `PVLive updated` truth values.

### status.py

`status.py` contains functionality for the `status pagwe` and allows the OCF team to update the forecast status in the database. This is one of the advantages of using an interface like Streamlit, facilitating status updates in a database.

### auth.py

`auth.py` contains code for the basic authenticaion that's been put in place.

### pvsite_forecast.py

`pvsite_forecast.py` contains the formulas and the metrics used to calculate MAE, nMAE and penalty incured against all sites.

### site_toolbox.py

`site_toolbox.py` is a page on the dashboard that can be used to get details of any particular site that OCF provides forecast to.

### plots/make_pinball_and_exceedance_plots.py

Function to make `pinball` and exceedance plots. This shows how good the probabilistic forecasts are doing.

### plots/ramp_rate.py

Function to make `ramp rate` plots.

## 🛠️ infrastructure

`.github/workflows` contains some CI actions.

1. `docker-pipeline.yml`: Creates and publishes a docker image.

With any push to `main`, in order to deploy changes, the `Terraform Cloud` variable is updated with the commit reference and deployed to `AWS Elastic Beanstalk`.

## Environmental Variables

- DB_URL: The database url which will be queried for forecasts
- password: The password for accessing the code
- SHOW_PVNET_GSP_SUM: Option to show `pvnet_gsp_sum` model or not. This defaults to zero
- REGION: Option can be UK or India. This effects the default values on the NWP and Satellite pages
- ENVIRONMENT: Option can be `development` or `production`.
  This effects the default values on the NWP and Satellite pages

## Develop

Currently this repository is only used by OCF for internal metric calculations, as it contiains client information. We hope to make it more freely useable in the near future.

### Tests

To run the tests, make sure you have `pytest` installed

```bash
pip install pytest
```

and then you can run

```bash
pytest
```

## Contributors and community

[![issues badge](https://img.shields.io/github/issues/openclimatefix/elexonpy?color=FFAC5F)](https://github.com/openclimatefix/elexonpy/issues?q=is%3Aissue+is%3Aopen+sort%3Aupdated-desc)

- PR's are welcome! See the [Organisation Profile](https://github.com/openclimatefix) for details on contributing
- Find out about our other projects in the [OCF Meta Repo](https://github.com/openclimatefix/ocf-meta-repo)
- Check out the [OCF blog](https://openclimatefix.org/blog) for updates
- Follow OCF on [LinkedIn](https://uk.linkedin.com/company/open-climate-fix)
- OCF templete: (https://github.com/openclimatefix/ocf-template?tab=readme-ov-file#contributing-and-community)

The following folks have contributed to this repo.

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/suleman1412"><img src="https://avatars.githubusercontent.com/u/37236131?v=4?s=100" width="100px;" alt="Suleman Karigar"/><br /><sub><b>Suleman Karigar</b></sub></a><br /><a href="https://github.com/openclimatefix/analysis-dashboard/commits?author=suleman1412" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/peterdudfield"><img src="https://avatars.githubusercontent.com/u/34686298?v=4?s=100" width="100px;" alt="Peter Dudfield"/><br /><sub><b>Peter Dudfield</b></sub></a><br /><a href="#projectManagement-peterdudfield" title="Project Management">📆</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/devsjc"><img src="https://avatars.githubusercontent.com/u/47188100?v=4?s=100" width="100px;" alt="devsjc"/><br /><sub><b>devsjc</b></sub></a><br /><a href="https://github.com/openclimatefix/analysis-dashboard/commits?author=devsjc" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://racheltipton.dev"><img src="https://avatars.githubusercontent.com/u/86949265?v=4?s=100" width="100px;" alt="rachel tipton"/><br /><sub><b>rachel tipton</b></sub></a><br /><a href="https://github.com/openclimatefix/analysis-dashboard/commits?author=rachel-labri-tipton" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/braddf"><img src="https://avatars.githubusercontent.com/u/41056982?v=4?s=100" width="100px;" alt="braddf"/><br /><sub><b>braddf</b></sub></a><br /><a href="https://github.com/openclimatefix/analysis-dashboard/commits?author=braddf" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/dfulu"><img src="https://avatars.githubusercontent.com/u/41546094?v=4?s=100" width="100px;" alt="James Fulton"/><br /><sub><b>James Fulton</b></sub></a><br /><a href="https://github.com/openclimatefix/analysis-dashboard/commits?author=dfulu" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ADIMANV"><img src="https://avatars.githubusercontent.com/u/68527614?v=4?s=100" width="100px;" alt="Aditya Sawant"/><br /><sub><b>Aditya Sawant</b></sub></a><br /><a href="https://github.com/openclimatefix/analysis-dashboard/commits?author=ADIMANV" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/MAYANK12SHARMA"><img src="https://avatars.githubusercontent.com/u/145884197?v=4?s=100" width="100px;" alt="MAYANK SHARMA"/><br /><sub><b>MAYANK SHARMA</b></sub></a><br /><a href="https://github.com/openclimatefix/analysis-dashboard/commits?author=MAYANK12SHARMA" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/AnujNayak108"><img src="https://avatars.githubusercontent.com/u/86143398?v=4?s=100" width="100px;" alt="Anuj Nayak"/><br /><sub><b>Anuj Nayak</b></sub></a><br /><a href="https://github.com/openclimatefix/analysis-dashboard/commits?author=AnujNayak108" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://www.linkedin.com/in/ram-from-tvl"><img src="https://avatars.githubusercontent.com/u/114728749?v=4?s=100" width="100px;" alt="Ramkumar R"/><br /><sub><b>Ramkumar R</b></sub></a><br /><a href="#infra-ram-from-tvl" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->
<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!

_Part of the [Open Climate Fix](https://github.com/orgs/openclimatefix/people) community._

[![OCF Logo](https://cdn.prod.website-files.com/62d92550f6774db58d441cca/6324a2038936ecda71599a8b_OCF_Logo_black_trans.png)](https://openclimatefix.org)

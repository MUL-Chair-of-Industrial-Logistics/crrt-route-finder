# Route finder for combined road-rail transportation

This repository contains an algorithm to find promising consolidation options for combined road-rail transportation in a
logistics network

For methodological details please refer to the corresponding publication:

* Miklautsch, P., Woschank, M. (2023). Decarbonizing Industrial Logistics Through a GIS-Based Approach for Identifying
  Pareto-Optimal Combined Road-Rail Transport Routes. In: Borgianni, Y., Molinaro, M., Orzes, G., Matt, D.T. (eds)
  Towards
  a Smart, Resilient and Sustainable Industry. ISIEA 2023. Springer, Cham. https://doi.org/10.1007/978-3-031-38274-1_31

## Link between the code and the methodology

* df_relations equals to V_R in the paper
* df_intersection_points equals to V_I in the paper
* df_sections equals to V_S in the paper
* df_contiguous_section_combinations equals to V_C in the paper

## How to use

1. Install the requirements with `pip install -r requirements.txt`
2. Create a file called utils/api_keys.py and insert the following lines:

- GOOGLE_API_KEY = 'your google api key'
- ORS_API_KEY = 'your openrouteservice api key'

You can get the Google API key from https://developers.google.com/maps/documentation/javascript/get-api-key
and the ORS API key from https://openrouteservice.org/dev/#/home

3. Change STEP 1 in main.py according to your input data. In the example, the input data is an Excel file having the
   specified columns. Anyways, the DataFrame needs to have the columns 'from_address', 'to_address', 'weight_in_tons',
   and 'date'
4. Run the code with `python main.py`
5. The plot then shows the evaluated possible combinations. For details (from, to, geometry), see the generated file
   temp/contiguous_section_combinations.json
6. Shift your freight to rail and save the world!

Created with the help of GitHub Copilot and OpenAI's ChatGPT

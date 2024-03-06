import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium
from folium.plugins import PolyLineTextPath
from geopy.distance import geodesic
from geopy.point import Point
from streamlit_folium import st_folium
import altair as alt
import math
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

coords = {
    "New York": (40.7128, -74.0060),
    "London": (51.5074, -0.1278),
    "Tokyo": (35.6895, 139.6917),
    "Paris": (48.8566, 2.3522),
    "Hong Kong": (22.3193, 114.1694),
    "Singapore": (1.3521, 103.8198),
    "Shanghai": (31.2304, 121.4737),
    "Dubai": (25.276987, 55.296249),
    "Beijing": (39.9042, 116.4074),
    "Sydney": (-33.8688, 151.2093),
    "Los Angeles": (34.0522, -118.2437),
    "Berlin": (52.5200, 13.4050),
    "Moscow": (55.7558, 37.6173),
    "Chicago": (41.8781, -87.6298),
    "Toronto": (43.6532, -79.3832),
    "Mumbai": (19.0760, 72.8777),
    "San Francisco": (37.7749, -122.4194),
    "Madrid": (40.4168, -3.7038),
    "São Paulo": (-23.5505, -46.6333),
    "Istanbul": (41.0082, 28.9784),
    "Barcelona": (41.3851, 2.1734),
    "Mexico City": (19.4326, -99.1332),
}
days_in_year = 365
caloric_supply_df = pd.read_csv('daily-caloric-supply-derived-from-carbohydrates-protein-and-fat.csv').drop(['Code'], axis=1)
ghg_per_kg_df = pd.read_csv('ghg-per-kg-poore.csv').drop(['Code', "Year"], axis=1)
annual_ghg_emissions_meatbased = 0
annual_ghg_emissions_plantbased = 0

def scrape_nyt_news():
    url = "https://www.nytimes.com/section/climate"

    response = requests.get(url)
    with open('response_content.txt', 'w') as file:
        file.write(response.text)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        script_tag = soup.find('script', {'type': 'application/ld+json'})
        data = json.loads(script_tag.text)
        articles = data['mainEntity']['itemListElement']
        for article in articles:
            title_segments = article['url']
            title_segments = title_segments.rsplit('/', 1)[-1].replace('.html', '')
            title_words = title_segments.split('-')
            title = ' '.join([word.capitalize() for word in title_words])
            article['title'] = title
        return articles
    else:
        print(response.content)
        print("Failed to fetch data from New York Times")

def find_start_coords(city):
    return coords.get(city)

def calculate_average_ghg(items, ghg_factors_df):
    if isinstance(items, str):  # If a single item is passed, make it a list
        items = [items]
    total_ghg = 0
    count = 0
    for item in items:
        filtered_df = ghg_factors_df[ghg_factors_df['Entity'] == item]
        if not filtered_df.empty:
            ghg_per_kg = filtered_df['GHG emissions per kilogram (Poore & Nemecek, 2018)'].iloc[0]
            total_ghg += ghg_per_kg
            count += 1
        else:
            print(f"Warning: '{item}' not found in GHG factors dataset.")
    return total_ghg / count if count > 0 else 0

def calculate_carbon_footprint_plant():
    daily_consumption_kg = {
        'Fruits': 400 / 1000,
        'Grains': 180 / 1000,
        'Vegetables': 400 / 1000, 
        'Legumes': 100 / 1000, 
    }

    annual_ghg_emissions_plantbased = 0
    for food, daily_kg in daily_consumption_kg.items():
        if food == 'Fruits':
            fruits_ghg_avg = calculate_average_ghg(['Apples', 'Bananas', 'Berries & Grapes', 'Citrus Fruit', 'Other Fruit'], ghg_per_kg_df)
            annual_ghg_emissions_plantbased += daily_kg * days_in_year * fruits_ghg_avg
        elif food == 'Grains':
            barley_ghg_per_kg = calculate_average_ghg(['Barley', 'Maize', 'Oatmeal', 'Rice', 'Wheat & Rye'], ghg_per_kg_df)
            annual_ghg_emissions_plantbased += daily_kg * days_in_year * barley_ghg_per_kg
        elif food == 'Vegetables':
            vegetables_ghg_avg = calculate_average_ghg(['Tomatoes', 'Other Vegetables', 'Brassicas', 'Onions & Leeks'], ghg_per_kg_df)
            annual_ghg_emissions_plantbased += daily_kg * days_in_year * vegetables_ghg_avg
        elif food == 'Legumes':
            # Using the approximate value directly, as before
            legumes_ghg_avg = calculate_average_ghg(['Groundnuts', 'Other Pulses', 'Peas'], ghg_per_kg_df)
            annual_ghg_emissions_plantbased += daily_kg * days_in_year * legumes_ghg_avg

    return annual_ghg_emissions_plantbased

def calculate_carbon_footprint_meat():
    data_2020 = caloric_supply_df[caloric_supply_df['Year'] == 2020]
    average_fat_intake = data_2020['Daily caloric intake per person from fat'].mean()
    average_animal_protein_intake = data_2020['Daily caloric intake per person that comes from animal protein'].mean()
    average_vegetal_protein_intake = data_2020['Daily caloric intake per person that comes from vegetal protein'].mean()
    average_carbohydrates_intake = data_2020['Daily caloric intake per person from carbohydrates'].mean()

    average_fat_intake_kg = (average_fat_intake / 9) / 1000
    average_animal_protein_intake_kg = (average_animal_protein_intake / 4) / 1000
    average_vegetal_protein_intake_kg = (average_vegetal_protein_intake / 4) / 1000
    average_carbohydrates_intake_kg = (average_carbohydrates_intake / 4) / 1000

    animal_protein_items = ['Beef (beef herd)', 'Poultry Meat', 'Pig Meat', 'Fish (farmed)', 'Eggs']
    fat_items = ['Cheese']
    vegetal_protein_items = ['Tofu', 'Other Pulses']
    carbohydrates_items = ['Rice', 'Wheat & Rye', 'Potatoes', 'Cassava']

    ghg_animal_protein_per_kg = calculate_average_ghg(animal_protein_items, ghg_per_kg_df)
    ghg_fat_per_kg = calculate_average_ghg(fat_items, ghg_per_kg_df)
    ghg_vegetal_protein_per_kg = calculate_average_ghg(vegetal_protein_items, ghg_per_kg_df)
    ghg_carbohydrates_per_kg = calculate_average_ghg(carbohydrates_items, ghg_per_kg_df)

    annual_fat_ghg_emissions = average_fat_intake_kg * days_in_year * ghg_fat_per_kg
    average_daily_total_ghg = (average_fat_intake_kg * ghg_fat_per_kg + 
                            average_animal_protein_intake_kg * ghg_animal_protein_per_kg + 
                            average_vegetal_protein_intake_kg * ghg_vegetal_protein_per_kg + 
                            average_carbohydrates_intake_kg * ghg_carbohydrates_per_kg)

    annual_fat_ghg_emissions = average_fat_intake_kg * days_in_year * ghg_fat_per_kg
    annual_carbohydrates_ghg_emissions = average_carbohydrates_intake_kg * days_in_year * ghg_carbohydrates_per_kg
    annual_animal_protein_ghg_emissions = average_animal_protein_intake_kg * days_in_year * ghg_animal_protein_per_kg
    annual_vegetal_protein_ghg_emissions = average_vegetal_protein_intake_kg * days_in_year * ghg_vegetal_protein_per_kg

    annual_ghg_emissions_meatbased = (annual_fat_ghg_emissions + annual_carbohydrates_ghg_emissions +
                                annual_animal_protein_ghg_emissions + annual_vegetal_protein_ghg_emissions)

    return annual_ghg_emissions_meatbased

def create_chart(data, y_field, title, color_scheme='tableau20'):
    chart = alt.Chart(data).mark_line().encode(
        x=alt.X('Year:O', axis=alt.Axis(title='Year')),
        y=alt.Y(f'{y_field}:Q', axis=alt.Axis(title='Calories')),
        color=alt.Color('Entity:N', scale=alt.Scale(scheme=color_scheme), legend=alt.Legend(title="Country")),
        tooltip=['Entity', 'Year', y_field]
    ).properties(
        title=title,
        width=300,
        height=200
    )
    
    return chart

with st.spinner(text="Loading..."):
    header = st.container()
    flight_simulator = st.container()
    trends = st.container()
    prediction = st.container()
    news = st.container()
    endnotes = st.container()

    with header:
        st.title("Carbon Footprint 👣 Diet Analysis 🌱")
        st.header("What is the comparative carbon footprint 👣 of plant-based diets versus meat-based diets?")
        st.markdown("What is the global impact on the planet? 🌎 Our approach to this challenge involved the use of various data sources. _Please refer to \"Endnotes\" section below to see more details on sources and diets considered_.")
        annual_ghg_emissions_meatbased = calculate_carbon_footprint_meat()
        annual_ghg_emissions_plantbased = calculate_carbon_footprint_plant()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Meat-based diet")
            st.metric(label="Annual GHG emissions", value=f"🥩 {format(annual_ghg_emissions_meatbased, '.1f')} kg CO2")

        with col2:
            st.subheader("Plant-based diet")
            st.metric(label="Annual GHG emissions", value=f"🌱 {format(annual_ghg_emissions_plantbased, '.1f')} kg CO2", delta="3.2x more efficient vs meat")

        ghg_emissions = [annual_ghg_emissions_meatbased, annual_ghg_emissions_plantbased]
        diet_types = ['Meat-based Diet', 'Plant-based Diet']

        chart_data = pd.DataFrame({
            'Diet': diet_types,
            'GHG (kg CO2)': ghg_emissions
        })

        bar_chart = alt.Chart(chart_data).mark_bar().encode(
            x='Diet',
            y='GHG (kg CO2)',
            color=alt.condition(
                alt.datum.Diet == 'Meat-based Diet', 
                alt.value('mediumvioletred'),
                alt.value('limegreen')
            )
        ).properties(
            title='Annual GHG Emissions: Meat-based vs Plant-based Diet'
        )
        st.altair_chart(bar_chart, use_container_width=True)
        
    with flight_simulator:
        st.header("✈️ Flight Simulator")
        st.markdown("Let's calculate the distance traveled by plane for one passenger 👤 in economy class.")
        equivalent_flight_distance_meat = annual_ghg_emissions_meatbased / 0.2300351582119538 # in kgCO2e
        equivalent_flight_distance_plant = annual_ghg_emissions_plantbased / 0.2300351582119538 # in kgCO2e
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Meat-based diet")
            st.metric(label="Annual equivalent flight distance", value=f"🥩 {format(equivalent_flight_distance_meat, '.2f')} km")

        with col2:
            st.subheader("Plant-based diet")
            st.metric(label="Annual equivalent flight distance", value=f"🌱 {format(equivalent_flight_distance_plant, '.2f')} km")
        st.subheader("Find the equivalent km flight!")
        st.markdown("Let's simulate the equivalent travel routes on a map for one passenger in economy class based on the carbon footprint 👣 of each diet.")
        city_name = st.selectbox('📍 Select a city as a start location:', sorted(list(coords.keys())), index=21)
        start_coords = find_start_coords(city_name)
        bearing = 0  # Example bearing (North)
        bearing_plant = 15

        m = folium.Map(location=[start_coords[0], start_coords[1]], zoom_start=3)
        new_end_point_meat = geodesic(kilometers=equivalent_flight_distance_meat).destination(Point(*start_coords), bearing)
        end_coords_meat = (new_end_point_meat.latitude, new_end_point_meat.longitude)
        new_end_point_plant = geodesic(kilometers=equivalent_flight_distance_plant).destination(Point(*start_coords), bearing_plant)
        end_coords_plant = (new_end_point_plant.latitude, new_end_point_plant.longitude)

        # Add markers and routes to the map
        folium.Marker(start_coords, popup=f'Start: {city_name}').add_to(m)
        folium.Marker(end_coords_meat, popup='End for Meat Eaters').add_to(m)
        route_meat = folium.PolyLine(locations=[start_coords, end_coords_meat], color='mediumvioletred').add_to(m)
        PolyLineTextPath(route_meat, '     Meat Eaters  → ', repeat=False, offset=15, attributes={'font-weight': 'bold', 'font-size': '14'}).add_to(m)
        folium.Marker(end_coords_plant, popup='End for Plant-based').add_to(m)
        route_plant = folium.PolyLine(locations=[start_coords, end_coords_plant], color='limegreen').add_to(m)
        PolyLineTextPath(route_plant, '     Plant-based  → ', repeat=False, offset=15, attributes={'font-weight': 'bold', 'font-size': '14'}).add_to(m)
        st_folium(m, width=725, height=500)
        st.subheader(f"How many one-way trips have the equivalent carbon footprint 👣 from {city_name} to...?")
        col1, col2 = st.columns(2)
        with col1:
            end_location = st.selectbox('📍 Select an end location:', sorted(list(coords.keys())))
            end_location_coords = find_start_coords(end_location)
            years_to_analyse = st.slider('Slide to select years to analyse', min_value=1, max_value=100)
            

        with col2:
            from geopy.distance import geodesic
            distance_km = geodesic(start_coords, end_location_coords).kilometers
            trips_meat = distance_km / equivalent_flight_distance_meat
            trips_plant = distance_km / equivalent_flight_distance_plant
            st.metric(label="Meat-eaters", value=f"🥩 {math.ceil(trips_meat*years_to_analyse)} trip(s)")
            st.metric(label="Plant-eaters", value=f"🌱 {math.ceil(trips_plant*years_to_analyse)} trip(s)")
            


    st.write("")  
    with trends:
        st.header("📈 Diet trends worldwide")
        st.markdown("Diets have changed significantly over the last 60 years, showing a rise in fat 🧀 and animal 🍗 protein calories, especially in the United States 🇺🇸, and an increase in vegetal 🫛 protein in China, highlighting potential areas for further dietary shift research. Carbohydrate 🍞 trends vary by country, suggesting influences from culture, economy, or policy.")

        entities = ['United States', 'China', 'United Kingdom', 'France', 'Mexico', 'Japan', 'Spain']
        filtered_data = caloric_supply_df[caloric_supply_df['Entity'].isin(entities)]

        fat_chart = create_chart(filtered_data, 'Daily caloric intake per person from fat', 'Daily Caloric Intake from Fat')
        animal_protein_chart = create_chart(filtered_data, 'Daily caloric intake per person that comes from animal protein', 'Daily Caloric Intake from Animal Protein')
        vegetal_protein_chart = create_chart(filtered_data, 'Daily caloric intake per person that comes from vegetal protein', 'Daily Caloric Intake from Vegetal Protein')
        carbohydrates_chart = create_chart(filtered_data, 'Daily caloric intake per person from carbohydrates', 'Daily Caloric Intake from Carbohydrates')

        col1, col2 = st.columns(2)
        with col1:
            st.altair_chart(fat_chart, use_container_width=True)
        with col2:
            st.altair_chart(animal_protein_chart, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            st.altair_chart(vegetal_protein_chart, use_container_width=True)
        with col4:
            st.altair_chart(carbohydrates_chart, use_container_width=True)

    with prediction:

        features = ['Year', 'Daily caloric intake per person that comes from vegetal protein',
                    'Daily caloric intake per person from fat', 'Daily caloric intake per person from carbohydrates']
        target = 'Daily caloric intake per person that comes from animal protein'
        X = caloric_supply_df[features]
        y = caloric_supply_df[target]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        error = mean_absolute_error(y_test, predictions)
        #print(f"Mean Absolute Error: {error}")
        
        calories_from_vegetal_protein_2030 = caloric_supply_df[caloric_supply_df['Year'] == caloric_supply_df['Year'].max()]['Daily caloric intake per person that comes from vegetal protein'].mean()
        calories_from_fat_2030 = caloric_supply_df[caloric_supply_df['Year'] == caloric_supply_df['Year'].max()]['Daily caloric intake per person from fat'].mean()
        calories_from_carbohydrates_2030 = caloric_supply_df[caloric_supply_df['Year'] == caloric_supply_df['Year'].max()]['Daily caloric intake per person from carbohydrates'].mean()
        
        #Make a prediction for 2030 using the model
        input_data_2030 = pd.DataFrame({
            'Year': ['2030'],
            'Daily caloric intake per person that comes from vegetal protein': [calories_from_vegetal_protein_2030],
            'Daily caloric intake per person from fat': [calories_from_fat_2030],
            'Daily caloric intake per person from carbohydrates': [calories_from_carbohydrates_2030]
        })
        prediction_2030 = model.predict(input_data_2030)
        calories_from_animal_protein_2020 = caloric_supply_df[caloric_supply_df['Year'] == caloric_supply_df['Year'].max()]['Daily caloric intake per person that comes from animal protein'].mean()
        #print(f"Predicted daily caloric intake from animal protein in 2020: {calories_from_animal_protein_2020} calories")
        #print(f"Predicted daily caloric intake from animal protein in 2030: {prediction_2030[0]} calories")
        #st.metric(label="Predicted daily caloric intake from animal protein in 2030", value=f"🥩 {format(prediction_2030[0], '.2f')} calories", delta=f'{(prediction_2030[0]-calories_from_animal_protein_2020)/calories_from_animal_protein_2020}')
        #st.caption('Predicted using Random Forest Regression 🌳')
        st.markdown("🥩 Meat-based diets still have the largest number of individuals in 2023. As the population naturally increases, our carbon emissions can only get worse 👎🏽.")
        dietary_choices_df = pd.read_csv('dietary-choices-uk.csv').drop(['Code'], axis=1)
        dietary_choices_df = dietary_choices_df[dietary_choices_df['Entity'] == 'All adults']
        dietary_choices_df['Flexitarian'] = dietary_choices_df['Flexitarian'].astype(int)
        dietary_choices_df['Plant-based / Vegan'] = dietary_choices_df['Plant-based / Vegan'].astype(int)
        dietary_choices_df['Pescetarian'] = dietary_choices_df['Pescetarian'].astype(int)
        dietary_choices_df['Vegetarian'] = dietary_choices_df['Vegetarian'].astype(int)
        diet_types = ['Flexitarian', 'None of these', 'Plant-based / Vegan', 'Meat eater', 'Pescetarian', 'Vegetarian']
        dietary_choices_df['Day'] = pd.to_datetime(dietary_choices_df['Day'])
        df_grouped = dietary_choices_df.groupby('Day').sum().reset_index()
        prediction_card_html = f"""
            <div style="border-radius: 10px; background-color: #cad7e8; padding-top: 20px; padding-left: 20px; padding-bottom: 20px;">
                <p style="color: black; font-size: large; margin: 0;">Predicted daily caloric intake from animal protein in 2030</p>
                <p style="color: black; font-size: xx-large; margin: 0;">🥩 {format(prediction_2030[0], '.2f')} calories</p>
                <p style="color: dimgray; font-size: small; margin: 0;">Predicted using Random Forest Regression 🌳</p>
            </div>
        """
        st.markdown(prediction_card_html, unsafe_allow_html=True)
        st.markdown(" ")
        st.markdown(" ")
        st.markdown(" ")

        

        df_long = df_grouped.melt('Day', var_name='Diet Type', value_name='Number of Individuals')
        chart = alt.Chart(df_long).mark_bar().encode(
            x=alt.X('yearmonth(Day):O', title='Month and Year'),
            y=alt.Y('sum(Number of Individuals):Q', title='Number of Individuals'),
            color=alt.Color('Diet Type:N', scale=alt.Scale(scheme='purpleblue'), legend=alt.Legend(title="Diet Types")),
            tooltip=[alt.Tooltip('monthdate(Day):T', title='Date'), 'Diet Type', 'Number of Individuals']
        ).properties(
            title='Diet Types Over Time'
        ).configure_axis(
            labelAngle=-45
        ).configure_legend(
            titleFontSize=12,
            labelFontSize=10
        )
        st.altair_chart(chart, use_container_width=True)

        st.markdown("ℹ️ Trends suggest an increase in population and a high share of meat-based diets in future therefore it is important for us to find more sustainable solutions for diets in the future, whether they include meat or not. We need to keep developing tech and update our knowledge on climate friendly solutions 📆.")
        
    with news:    
        list_of_headlines = []
        news_headlines = scrape_nyt_news()
        st.subheader("📰 Keep up with climate change news!")
        selected_value = st.slider('Slide to select number of headlines to view', min_value=1, max_value=len(news_headlines))
        
        if news_headlines:
            for headline in news_headlines[6:6+selected_value]:
                list_of_headlines.append(headline)
                news_card_html = f"""
                <div style="border-radius: 10px; background-color: #f9f9f9; padding: 20px; margin: 10px 0;">                
                    <a href="{headline['url']}" style="text-decoration: none; color: inherit;">
                        <h2 style="color: #333; font-size: 20px; margin: 0;">{headline['title']}</h2>
                    </a>
                    <p style="color: #777; font-size: 12px; margin: 10px 0 0;">New York Times - Extracted on: {datetime.now().strftime("%d %B")}</p>
                </div>
                """
                st.markdown(news_card_html, unsafe_allow_html=True)
    
    st.markdown(" ")
    st.markdown(" ")
    with endnotes:        
        st.header("📝 Endnotes and Data Sources")
        st.markdown("Distance traveled by plane for one passenger in economy class, using the [ADEME](https://www.ademe.fr/en/frontpage/) emission factor of 0.23 kilogram of carbon dioxide equivalent emitted per kilometer.")
        st.markdown("Prediction for 2023 trend in animal protein intake was created using a Random Forest Regressor 🌳 based on the latest caloric data of fat, carbohydrates and vegetal protein.")
        st.markdown("Our data source for vegetarian diets: [Mayo Clinic](https://www.mayoclinic.org/healthy-lifestyle/nutrition-and-healthy-eating/in-depth/vegetarian-diet/art-20046446).")
        st.markdown("Our data source for the news is: [New York Times](https://www.nytimes.com/section/climate).")
        st.markdown("Our data source for co2 emissions is: [Kaggle](https://www.kaggle.com/datasets/alessandrolobello/agri-food-co2-emission-dataset-forecasting-ml).")
        st.markdown("Our data source for diet compositions is: [Our World in Data](https://ourworldindata.org/diet-compositions#all-charts).")
        st.markdown("Our data source for the dietary choices is: [Our World in Data](https://ourworldindata.org/grapher/dietary-choices-uk).")
        st.subheader("💥 We hope you enjoyed the simulator!")
        #st.markdown("Elena Ginebra and Anastasia Krivenkovskaya")
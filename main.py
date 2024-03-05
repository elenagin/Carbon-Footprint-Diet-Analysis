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

def scrape_yahoo_finance_news():
    #url = "https://www.nytimes.com/section/climate"
    url_reuters = "https://www.reuters.com/sustainability/"

    response = requests.get(url)
    with open('response_content.txt', 'w') as file:
        file.write(response.text)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        headlines = soup.find_all('h3')
        news_headlines = [headline.get_text() for headline in headlines]
        return news_headlines
    else:
        print(response.content)
        print("Failed to fetch data from Yahoo Finance")

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


header = st.container()
flight_simulator = st.container()
environmental_news = st.container()
test = st.container()


with header:
    st.title("Carbon Footprint Diet Analysis 🌱")
    st.header("What is the comparative carbon footprint of plant-based diets versus meat-based diets?")
    st.markdown("What is the global impact on the planet? 🌎 Our approach to this challenge involved the use of various data sources.")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Meat-based diet")
        st.metric(label="Annual GHG emissions", value="🥩 1557 kg CO2")

    with col2:
        st.subheader("Plant-based diet")
        st.metric(label="Annual GHG emissions", value="🌱 479 kg CO2")

    labels = ['Meat-based Diet', 'Plant-based Diet']
    ghg_emissions = [1557, 479]
    fig, ax = plt.subplots()
    #plt.figure(figsize=(5, 2))
    plt.bar(labels, ghg_emissions, color=['crimson', 'limegreen'])
    plt.title('Annual GHG Emissions: Meat-based vs Plant-based Diet')
    plt.ylabel('GHG (kg CO2)')
    st.pyplot(fig)
    
   
    
with flight_simulator:
    st.header("Flight Simulator ✈️")
    st.subheader("Find the equivalent km flight!")
    st.selectbox('Select start location:', ['Barcelona','New York', 'London'])
    st.selectbox('Select timeframe:', ['1 year','1 month', '5 years'])
    start_coords = (41.3851, 2.1734)  # Example start coordinates (Barcelona)
    bearing = 0  # Example bearing (North)
    bearing_plant = 15

    # Initialize a map centered around the start location
    m = folium.Map(location=[41.3851, 2.1734], zoom_start=5)

    # Example distances for demonstration
    equivalent_flight_distance_meat = 1000  # Example distance for meat diet
    equivalent_flight_distance_plant = 500  # Example distance for plant diet

    # Calculate new end points based on distances
    new_end_point_meat = geodesic(kilometers=equivalent_flight_distance_meat).destination(Point(*start_coords), bearing)
    end_coords_meat = (new_end_point_meat.latitude, new_end_point_meat.longitude)

    new_end_point_plant = geodesic(kilometers=equivalent_flight_distance_plant).destination(Point(*start_coords), bearing_plant)
    end_coords_plant = (new_end_point_plant.latitude, new_end_point_plant.longitude)

    # Add markers and routes to the map
    folium.Marker(start_coords, popup='Start: Barcelona').add_to(m)
    folium.Marker(end_coords_meat, popup='End for Meat Eaters').add_to(m)
    route_meat = folium.PolyLine(locations=[start_coords, end_coords_meat], color='crimson').add_to(m)
    PolyLineTextPath(route_meat, '     Meat Eaters', repeat=False, offset=-10, attributes={'font-weight': 'bold', 'font-size': '14'}).add_to(m)

    folium.Marker(end_coords_plant, popup='End for Vegetarians').add_to(m)
    route_plant = folium.PolyLine(locations=[start_coords, end_coords_plant], color='limegreen').add_to(m)
    PolyLineTextPath(route_plant, '     Vegetarian', repeat=False, offset=10, attributes={'font-weight': 'bold', 'font-size': '14'}).add_to(m)

    # Display the map in Streamlit
    st_folium(m, width=725, height=500)

    
with environmental_news:
    list_of_headlines = []
    news_headlines = scrape_nyt_news()
    st.subheader("📰 Keep up with climate change news!")
    selected_value = st.slider('Slide to select number of headlines', min_value=1, max_value=len(news_headlines))
    
    if news_headlines:
        for headline in news_headlines[6:6+selected_value]:
            list_of_headlines.append(headline)
            news_card_html = f"""
            <div style="border-radius: 10px; background-color: #f9f9f9; padding: 20px; margin: 10px 0;">                
                <a href="{headline['url']}" style="text-decoration: none; color: inherit;">
                    <h2 style="color: #333; font-size: 20px; margin: 0;">{headline['title']}</h2>
                </a>
                <p style="color: #777; font-size: 12px; margin: 10px 0 0;">New York Times - {datetime.now().strftime("%d %B")}</p>
            </div>
            """
            st.markdown(news_card_html, unsafe_allow_html=True)

        
st.subheader("Hope you enjoyed our simulator!")
st.text("Elena Ginebra and Anastasia Krivenkovskaya, Elena Ginebra")

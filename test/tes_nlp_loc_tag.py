import locationtagger

# Sample Indonesian text
text = "Presiden Joko Widodo mengunjungi kota Surabaya, Jawa Timur, untuk meresmikan proyek infrastruktur."

# Extracting entities
entities = locationtagger.find_locations(text = text)

# Getting all countries, regions, and cities
print("Countries:", entities.countries)
print("Regions:", entities.regions)
print("Cities:", entities.cities)

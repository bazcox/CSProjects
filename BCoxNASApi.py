import requests
from PIL import Image
from io import BytesIO
import random
import datetime

# Function to get available cameras for each rover
def get_available_cameras(rover):
    cameras = {
        'Curiosity': ['FHAZ', 'RHAZ', 'MAST', 'CHEMCAM', 'MAHLI', 'MARDI', 'NAVCAM'],
        'Opportunity': ['FHAZ', 'RHAZ', 'NAVCAM', 'PANCAM', 'MINITES'],
        'Spirit': ['FHAZ', 'RHAZ', 'NAVCAM', 'PANCAM', 'MINITES']
    }
    return cameras.get(rover, [])

# Function to calculate the current Martian sol for Curiosity
def calculate_curiosity_sol():
    landing_date = datetime.datetime(2012, 8, 6)
    current_date = datetime.datetime.now()
    sol = (current_date - landing_date).days
    return sol

# Rover sol ranges
sol_ranges = {
    'Curiosity': (0, calculate_curiosity_sol()),
    'Opportunity': (0, 5111),
    'Spirit': (0, 2208)
}

# Ask the user to choose a rover
print("Choose a rover: Curiosity, Opportunity, Spirit")
rover = input("Enter rover name: ").capitalize()

# Validate rover choice
if rover not in ['Curiosity', 'Opportunity', 'Spirit']:
    print("Invalid rover name.")
else:
    # Display sol range for the chosen rover
    print(f"Enter a sol number between {sol_ranges[rover][0]} and {sol_ranges[rover][1]} for the {rover} rover.")
    sol = int(input("Enter sol number: "))

    # Validate sol input
    if not (sol_ranges[rover][0] <= sol <= sol_ranges[rover][1]):
        print(f"Invalid sol number. Please enter a number between {sol_ranges[rover][0]} and {sol_ranges[rover][1]}.")
    else:
        # Get available cameras for the chosen rover
        available_cameras = get_available_cameras(rover)
        print(f"Available cameras for {rover}: {', '.join(available_cameras)}")

        # Ask the user to choose a camera
        camera = input("Enter camera name: ").upper()

        # Validate camera choice
        if camera not in available_cameras:
            print("Invalid camera name.")
        else:
            # Your personal API key
            api_key = 'iivmRty46kRgROckJqqMGL6ruVDF0Qaq1772aszG'

            # API endpoint
            url = f'https://api.nasa.gov/mars-photos/api/v1/rovers/{rover}/photos'

            # Parameters for the API request
            params = {
                'sol': sol,
                'camera': camera.lower(),
                'api_key': api_key
            }

            # Making the GET request
            response = requests.get(url, params=params)

            # Check if the request was successful
            if response.status_code == 200:
                # Convert the response to JSON
                data = response.json()

                # Extract image URLs
                image_urls = [photo['img_src'] for photo in data['photos']]

                # Check if there are any images
                if image_urls:
                    # Select a random image URL
                    random_img_url = random.choice(image_urls)

                    # Display or download the selected image
                    response = requests.get(random_img_url)
                    img = Image.open(BytesIO(response.content))
                    img.show()  # or img.save("filename.jpg") to save the image
                else:
                    print("No images found for the given criteria")

            else:
                print("Failed to retrieve data from NASA API")

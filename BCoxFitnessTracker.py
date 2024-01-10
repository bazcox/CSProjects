import datetime
import json

class FitnessApp:
    def __init__(self, filename='workouts.txt'):
        # Initialize the FitnessApp with a filename, defaulting to 'workouts.txt'
        self.filename = filename
        # Load existing workouts from the file upon initialization
        self.workouts = self.load_workouts()

    def load_workouts(self):
        try:
            with open(self.filename, 'r') as file:
                data = json.load(file)
                # Converting string dates in JSON to datetime.date objects
                return {datetime.datetime.strptime(k, '%d-%m-%Y').date(): v for k, v in data.items()}
        except (FileNotFoundError, json.JSONDecodeError):
            # Return an empty dictionary if file not found or JSON is invalid
            return {}

    def save_workouts(self):
        with open(self.filename, 'w') as file:
            # Convert datetime.date objects back to strings for JSON serialization
            data = {k.strftime('%d-%m-%Y'): v for k, v in self.workouts.items()}
            # Write the updated workouts data to the file
            json.dump(data, file)

    def add_workout(self):
        # Prompt user to input workout details
        date = input("Enter the date for the workout (DD-MM-YYYY): ")
        try:
            # Parse input date string to datetime.date object
            workout_date = datetime.datetime.strptime(date, "%d-%m-%Y").date()
        except ValueError:
            # Handle invalid date format
            print("Invalid date format. Please use DD-MM-YYYY.")
            return

        # Collect workout details from the user
        exercise = input("Enter exercise name: ")
        sets = int(input("Enter number of sets: "))
        reps = int(input("Enter number of reps per set: "))
        weight = float(input("Enter weight used (in lbs): "))

        # Create a workout record
        workout = {
            'exercise': exercise,
            'sets': sets,
            'reps': reps,
            'weight': weight
        }

        # Add workout to the appropriate date
        if workout_date not in self.workouts:
            self.workouts[workout_date] = []
        self.workouts[workout_date].append(workout)

        # Save updated workouts back to file
        self.save_workouts()
        print("Workout added successfully.")

    def delete_workout(self):
        # Prompt the user to input the date of the workout to be deleted
        date = input("Enter the date of the workout to delete (DD-MM-YYYY): ")
        try:
            # Convert the input date string to a datetime.date object
            workout_date = datetime.datetime.strptime(date, "%d-%m-%Y").date()
        except ValueError:
            # Handle invalid date format and return to the main menu
            print("Invalid date format. Please use DD-MM-YYYY.")
            return

        # Check if there are workouts on the entered date
        if workout_date not in self.workouts:
            print("No workouts found for this date.")
            return

        # Display the workouts scheduled on the specified date
        self.display_workouts_on_date(workout_date)

        try:
            # Ask the user to choose which workout to delete
            workout_index = int(input("Enter the workout number to delete: ")) - 1
            # Validate the entered workout number
            if workout_index >= len(self.workouts[workout_date]) or workout_index < 0:
                print("Invalid workout number.")
                return
            # Delete the selected workout
            del self.workouts[workout_date][workout_index]
            # Save the updated workouts list to the file
            self.save_workouts()
            print("Workout deleted successfully.")
        except ValueError:
            # Handle non-integer inputs for workout number
            print("Please enter a valid number.")

    def display_workouts_on_date(self, workout_date):
        # Print the workouts scheduled for a specific date
        print(f"Workouts for {workout_date.strftime('%d-%m-%Y')}:")
        for idx, workout in enumerate(self.workouts[workout_date], start=1):
            # Display each workout with its details
            print(f"  {idx}. {workout['exercise']} - Sets: {workout['sets']}, Reps: {workout['reps']}, Weight: {workout['weight']} lbs")

    def view_workouts(self):
        # Check if there are any workouts to display
        if not self.workouts:
            print("No workouts found.")
            return
        # Display all workouts
        for date, workouts in self.workouts.items():
            formatted_date = date.strftime("%d-%m-%Y")
            print(f"\nDate: {formatted_date}")
            for idx, workout in enumerate(workouts, start=1):
                print(f"  Workout {idx}: {workout['exercise']} - Sets: {workout['sets']}, Reps: {workout['reps']}, Weight: {workout['weight']} lbs")

    def view_daily_workout(self, date):
        # Parse input date string to datetime.date object
        try:
            workout_date = datetime.datetime.strptime(date, "%d-%m-%Y").date()
        except ValueError:
            print("Invalid date format. Please use DD-MM-YYYY.")
            return

        # Display workouts for a specific date
        if workout_date in self.workouts:
            print(f"Workouts for {workout_date.strftime('%d-%m-%Y')}:")
            for workout in self.workouts[workout_date]:
                print(f"  {workout['exercise']} - Sets: {workout['sets']}, Reps: {workout['reps']}, Weight: {workout['weight']} lbs")
        else:
            print("No workouts found for this date.")

def main():
    app = FitnessApp()
    while True:
        # User interface for the fitness tracker
        print("\nFitness Tracker")
        print("1. Add a workout")
        print("2. View all workouts")
        print("3. View workouts for a specific date")
        print("4. Delete a workout")
        print("5. Exit")
        choice = input("Enter your choice: ")

        # Handling user input for different functionalities
        if choice == '1':
            app.add_workout()
        elif choice == '2':
            app.view_workouts()
        elif choice == '3':
            date = input("Enter the date to view workouts (DD-MM-YYYY): ")
            app.view_daily_workout(date)
        elif choice == '4':
            app.delete_workout()
        elif choice == '5':
            # Exit the application
            break
        else:
            # Handle invalid user input
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()

import os

def is_package_installed(package_name):
    """
    Checks if the given package is already installed in the current Python environment.
    
    Parameters:
    - package_name (str): Name of the package to check.
    
    Returns:
    - bool: True if the package is installed, False otherwise.
    """
    installed_packages = os.popen('pip freeze').read()
    return package_name in installed_packages

def install_from_requirements():
    """
    Reads the 'dependencies.txt' file to get a list of required packages.
    Installs each package if it's not already installed in the current Python environment.
    
    Note:
    This function assumes the 'dependencies.txt' has entries in the format 'package==version'.
    Adjust as needed for other formats.
    """
    # Read the list of packages from the 'dependencies.txt' file
    with open("dependencies.txt", "r") as f:
        packages = f.readlines()

    # Iterate through the list of packages
    for package in packages:
        package_name = package.split('==')[0].strip()
        if not is_package_installed(package_name):
            # If the package is not installed, install it
            print(f"Installing {package_name}...")
            os.system(f'pip install {package}')
            print(f"{package_name} installed successfully.")
        else:
            # If the package is already installed, skip the installation
            print(f"{package_name} is already installed.")

# Install required packages from the dependencies.txt file
print("Starting installation of required packages...")
install_from_requirements()
print("All required packages have been processed.")


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

def configure_driver():
    """Configure et retourne le driver Chrome"""
    options = Options()
    options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Ajouter des options pour éviter la détection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

def login_to_instagram(driver, username, password):
    """Se connecte à Instagram"""
    try:
        # Aller sur la page de connexion
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(5)  # Attendre le chargement
        
        # Remplir le formulaire de connexion
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        password_field = driver.find_element(By.NAME, "password")
        
        username_field.send_keys(username)
        password_field.send_keys(password)
        
        # Cliquer sur le bouton de connexion
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        
        time.sleep(5)  # Attendre la connexion
        return True
    except Exception as e:
        print(f"Erreur lors de la connexion: {e}")
        return False

def get_followers(driver, target_account):
    """Récupère les followers d'un compte cible"""
    try:
        # Aller sur la page du compte cible
        driver.get(f"https://www.instagram.com/{target_account}/")
        time.sleep(5)
        
        # Cliquer sur le bouton des followers
        followers_link = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/followers/')]"))
        )
        followers_link.click()
        
        time.sleep(3)  # Attendre l'ouverture de la fenêtre des followers
        print(f"Accès aux followers de {target_account} réussi")
        
    except Exception as e:
        print(f"Erreur lors de l'accès aux followers: {e}")

def main():
    # Informations de connexion en dur
    username = "dailyof_rudemiss"
    password = "Bienvenu@227"
    target_account = "razack_yamass"
    
    driver = None
    try:
        # Initialiser le driver
        driver = configure_driver()
        
        # Se connecter
        if login_to_instagram(driver, username, password):
            print("Connexion réussie")
            # Récupérer les followers
            get_followers(driver, target_account)
        else:
            print("Échec de la connexion")
            
    except Exception as e:
        print(f"Une erreur est survenue: {e}")
        
    finally:
        # Fermer le navigateur
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()

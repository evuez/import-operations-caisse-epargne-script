import-operations-caisse-epargne-script
=======================================

Import en QIF ou CSV des transactions d'un compte caisse d'épargne avec parser pour les fichiers QIF

## Paramètres

Les paramètres de connexion suivant doivent être défini dans un fichier settings.py dans le même format que le fichier example.settings.py

 * Votre identifiant client
 * Votre code client
 * Votre numéro de compte (IBAN)

## Test

La méthode `get_transactions([from_days_ago, [to_days_ago]])` renvoie le fichier QIF ou CSV de l'intervalle donné. Si aucun paramètre ne lui est passé, elle utilise l'intervalle maximal (jour courant - 60, jour courant - 1)

    bank = Bank(CLIENT_ID, CLIENT_SECRET, CLIENT_IBAN)

    # intervalle maximal
    print bank.get_transactions()

    # transactions des 6 derniers jours
    print bank.get_transactions(7, 1)
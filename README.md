Import de transactions Caisse d'épargne
=======================================
### Import en QIF ou CSV des transactions d'un compte caisse d'épargne avec parseur pour les fichiers QIF

*Ce script est une adpatation en python du script d'[esion][1] disponible à l'adresse suivante https://github.com/esion/import-operations-caisse-epargne-script*

*Il fonctionne avec la version actuelle (novembre 2013) du site de la caisse d'épargne*

## Paramètres

Les paramètres de connexion suivant doivent être défini dans un fichier settings.py dans le même format que le fichier example.settings.py

 * Votre identifiant client
 * Votre code client
 * Votre numéro de compte (IBAN)

## Fonctionnalités

La méthode `get_transactions([from_days_ago, [to_days_ago]])` renvoie le fichier QIF ou CSV de l'intervalle donné. Si aucun paramètre ne lui est passé, elle utilise l'intervalle maximal (jour courant - 60, jour courant - 1)

### Principales

    bank = Bank(CLIENT_ID, CLIENT_SECRET, CLIENT_IBAN)

    # intervalle maximal
    print bank.get_transactions()

    # transactions des 6 derniers jours
    print bank.get_transactions(7, 1)

    # utilisation du parseur pour afficher les transactions
    for t in Transactions(qif_str=bank.get_transactions()):
        print '{0}: {1}'.format(t.date, t.amount)

    # en utilisant un fichier
    for t in Transactions('transactions.qif'):
        print '{0}: {1}'.format(t.date, t.amount)

### Autres

    bank = Bank(CLIENT_ID, CLIENT_SECRET, CLIENT_IBAN)

    transactions = Transactions()

    transactions.load_qif(qif_file='transactions.qif') # chargement d'un fichier QIF
    transactions.load_qif(qif_str=bank.get_transactions()) # écrase le premier chargement

    transactions += Transaction() # ajoute une transaction vide

    transactions.next() # retourne la transaction suivante et déplace le curseur
    transactions.current() # retourne la transaction au niveau du curseur

    transactions.first() # retourne la première transaction, ne déplace pas le curseur
    transactions.last() # retourne la dernière transaction, ne déplace pas le curseur
    transactions[3] # retourne la troisième transaction, ne déplace pas le curseur



  [1]: https://github.com/esion
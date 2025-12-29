"""
Script pour visualiser et analyser les coûts Apify
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from colorama import init, Fore, Style

# Initialiser colorama pour Windows
init()

def load_cost_tracking():
    """Charger le fichier de tracking des coûts"""
    file_path = Path("data/output/cost_tracking.json")
    
    if not file_path.exists():
        print(f"{Fore.RED}❌ Fichier de tracking non trouvé: {file_path}{Style.RESET_ALL}")
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def display_cost_dashboard(data):
    """Afficher un dashboard des coûts"""
    
    session_cost = data.get('session_cost', 0)
    budget_limit = data.get('budget_limit', 5.0)
    budget_used = (session_cost / budget_limit * 100) if budget_limit > 0 else 0
    remaining = budget_limit - session_cost
    
    # Déterminer la couleur selon le niveau
    if budget_used >= 90:
        color = Fore.RED
        status = "🔴 CRITIQUE"
    elif budget_used >= 80:
        color = Fore.YELLOW
        status = "🟠 ATTENTION"
    elif budget_used >= 60:
        color = Fore.LIGHTYELLOW_EX
        status = "🟡 SURVEILLER"
    else:
        color = Fore.GREEN
        status = "🟢 OK"
    
    # En-tête
    print("\n" + "="*80)
    print(f"{Fore.CYAN}💰 DASHBOARD DES COÛTS APIFY{Style.RESET_ALL}")
    print("="*80 + "\n")
    
    # Budget
    bar_length = 50
    filled = int(bar_length * budget_used / 100)
    bar = f"{color}{'█' * filled}{Style.RESET_ALL}{'░' * (bar_length - filled)}"
    
    print(f"{Fore.CYAN}📊 BUDGET: {color}{status}{Style.RESET_ALL}")
    print(f"   [{bar}] {color}{budget_used:.1f}%{Style.RESET_ALL}")
    print(f"   Utilisé: {color}${session_cost:.4f}{Style.RESET_ALL} / ${budget_limit:.2f}")
    print(f"   Restant: {Fore.GREEN}${remaining:.4f}{Style.RESET_ALL}")
    
    # Clients
    clients_count = len(data.get('clients', {}))
    avg_cost = session_cost / clients_count if clients_count > 0 else 0
    
    print(f"\n{Fore.CYAN}👥 CLIENTS TRAITÉS:{Style.RESET_ALL}")
    print(f"   Total: {clients_count} clients")
    print(f"   Coût moyen: ${avg_cost:.4f} par client")
    
    # Batches
    batches = data.get('batches', [])
    print(f"\n{Fore.CYAN}📦 BATCHES:{Style.RESET_ALL}")
    print(f"   Complétés: {len(batches)}")
    
    if batches:
        print(f"\n{Fore.CYAN}📈 HISTORIQUE DES BATCHES:{Style.RESET_ALL}")
        print(f"   {'Batch':<10} {'Coût':<12} {'Clients':<10} {'$/Client':<12} {'Total Session':<15}")
        print(f"   {'-'*60}")
        
        for batch in batches:
            batch_num = batch.get('batch_number', '?')
            cost = batch.get('cost', 0)
            clients = batch.get('clients_count', 0)
            avg = batch.get('avg_cost_per_client', 0)
            total = batch.get('session_total', 0)
            
            print(f"   #{batch_num:<9} ${cost:<11.4f} {clients:<10} ${avg:<11.4f} ${total:<14.4f}")
    
    # Estimation
    if batches:
        recent_batches = batches[-3:]
        avg_costs = [b['avg_cost_per_client'] for b in recent_batches if b.get('clients_count', 0) > 0]
        
        if avg_costs:
            avg_cost_per_client = sum(avg_costs) / len(avg_costs)
            estimated_clients = int(remaining / avg_cost_per_client) if avg_cost_per_client > 0 else 0
            
            print(f"\n{Fore.CYAN}🎯 ESTIMATION:{Style.RESET_ALL}")
            print(f"   Clients restants possibles: ~{Fore.GREEN}{estimated_clients}{Style.RESET_ALL} clients")
            print(f"   (basé sur moyenne: ${avg_cost_per_client:.4f}/client)")
    
    # Alertes
    warnings = data.get('warnings', [])
    if warnings:
        print(f"\n{Fore.YELLOW}⚠️  ALERTES BUDGÉTAIRES: {len(warnings)}{Style.RESET_ALL}")
        for warning in warnings[-3:]:  # 3 dernières alertes
            timestamp = warning.get('timestamp', '')
            message = warning.get('message', '')
            print(f"   • {timestamp}: {message}")
    
    # Métadonnées
    print(f"\n{Fore.CYAN}ℹ️  INFORMATIONS:{Style.RESET_ALL}")
    print(f"   Début session: {data.get('start_time', 'N/A')}")
    print(f"   Dernière MAJ: {data.get('last_update', 'N/A')}")
    
    print("\n" + "="*80 + "\n")


def display_recommendations(data):
    """Afficher des recommandations d'optimisation"""
    session_cost = data.get('session_cost', 0)
    budget_limit = data.get('budget_limit', 5.0)
    budget_used = (session_cost / budget_limit * 100) if budget_limit > 0 else 0
    batches = data.get('batches', [])
    
    print(f"{Fore.CYAN}💡 RECOMMANDATIONS D'OPTIMISATION:{Style.RESET_ALL}\n")
    
    # Analyse du coût par client
    if batches:
        avg_costs = [b['avg_cost_per_client'] for b in batches if b.get('clients_count', 0) > 0]
        if avg_costs:
            max_cost = max(avg_costs)
            min_cost = min(avg_costs)
            
            if max_cost > min_cost * 2:
                print(f"   {Fore.YELLOW}⚠️  Variation importante des coûts:{Style.RESET_ALL}")
                print(f"      Min: ${min_cost:.4f} | Max: ${max_cost:.4f}")
                print(f"      → Certains clients consomment beaucoup plus de ressources")
                print(f"      → Considérer un timeout plus strict ou une limite d'items\n")
    
    # Recommandations selon le budget
    if budget_used >= 80:
        print(f"   {Fore.RED}🔴 Budget critique!{Style.RESET_ALL}")
        print(f"      → Réduire la taille des batches")
        print(f"      → Ajouter max_items=100 dans search_ads_by_domain()")
        print(f"      → Réduire memory_mb=256 pour les petits clients\n")
    elif budget_used >= 60:
        print(f"   {Fore.YELLOW}🟡 Budget à surveiller{Style.RESET_ALL}")
        print(f"      → Envisager des limites sur le nombre d'ads par client")
        print(f"      → Vérifier les clients qui coûtent le plus cher\n")
    else:
        print(f"   {Fore.GREEN}🟢 Budget sain{Style.RESET_ALL}")
        print(f"      → Continuer avec les paramètres actuels")
        print(f"      → Possibilité d'augmenter la taille des batches si souhaité\n")
    
    # Optimisations générales
    print(f"   {Fore.CYAN}📋 Optimisations générales:{Style.RESET_ALL}")
    print(f"      1. Utiliser max_items pour limiter le scraping (ex: max_items=200)")
    print(f"      2. Réduire memory_mb pour les petits sites (256-512 MB)")
    print(f"      3. Définir un timeout_secs strict (180-300s)")
    print(f"      4. Traiter les gros clients séparément avec des limites spécifiques")
    print(f"      5. Surveiller le fichier cost_tracking.json régulièrement\n")
    
    print("="*80 + "\n")


def export_cost_report(data, output_file="cost_report.txt"):
    """Exporter un rapport des coûts dans un fichier"""
    output_path = Path("data/output") / output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("RAPPORT DES COÛTS APIFY\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        session_cost = data.get('session_cost', 0)
        budget_limit = data.get('budget_limit', 5.0)
        clients_count = len(data.get('clients', {}))
        batches = data.get('batches', [])
        
        f.write(f"Budget utilisé: ${session_cost:.4f} / ${budget_limit:.2f}\n")
        f.write(f"Budget restant: ${budget_limit - session_cost:.4f}\n")
        f.write(f"Clients traités: {clients_count}\n")
        f.write(f"Batches complétés: {len(batches)}\n\n")
        
        if batches:
            f.write("DÉTAIL DES BATCHES:\n")
            f.write("-" * 80 + "\n")
            for batch in batches:
                f.write(f"Batch #{batch.get('batch_number')}: ")
                f.write(f"${batch.get('cost', 0):.4f} ")
                f.write(f"({batch.get('clients_count', 0)} clients, ")
                f.write(f"${batch.get('avg_cost_per_client', 0):.4f}/client)\n")
    
    print(f"{Fore.GREEN}✅ Rapport exporté: {output_path}{Style.RESET_ALL}\n")


def main():
    """Fonction principale"""
    data = load_cost_tracking()
    
    if not data:
        return
    
    # Afficher le dashboard
    display_cost_dashboard(data)
    
    # Afficher les recommandations
    display_recommendations(data)
    
    # Proposer l'export
    if len(sys.argv) > 1 and sys.argv[1] == '--export':
        export_cost_report(data)


if __name__ == "__main__":
    main()

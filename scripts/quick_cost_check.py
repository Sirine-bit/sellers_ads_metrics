"""
Script rapide pour afficher un résumé des coûts en temps réel
Usage: python scripts/quick_cost_check.py
"""
import json
from pathlib import Path

def main():
    cost_file = Path("data/output/cost_tracking.json")
    
    if not cost_file.exists():
        print("❌ Aucun fichier de coûts trouvé. Lancez d'abord phase1_main.py")
        return
    
    with open(cost_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    session_cost = data.get('session_cost', 0)
    budget = data.get('budget_limit', 5.0)
    percentage = (session_cost / budget * 100) if budget > 0 else 0
    remaining = budget - session_cost
    clients = len(data.get('clients', {}))
    batches = len(data.get('batches', []))
    
    # Icône selon le niveau
    if percentage >= 90:
        icon = "🔴"
    elif percentage >= 80:
        icon = "🟠"
    elif percentage >= 60:
        icon = "🟡"
    else:
        icon = "🟢"
    
    # Estimation
    estimated = None
    if batches > 0:
        recent = data['batches'][-3:]
        avg_costs = [b['avg_cost_per_client'] for b in recent if b.get('clients_count', 0) > 0]
        if avg_costs:
            avg = sum(avg_costs) / len(avg_costs)
            estimated = int(remaining / avg) if avg > 0 else 0
    
    # Affichage compact
    print(f"\n{icon} Budget: ${session_cost:.4f}/${budget:.2f} ({percentage:.1f}%) | "
          f"Restant: ${remaining:.4f} | "
          f"Clients: {clients} | "
          f"Batches: {batches}", end="")
    
    if estimated:
        print(f" | Estimation: ~{estimated} clients restants")
    else:
        print()
    
    # Moyenne
    if clients > 0:
        avg = session_cost / clients
        print(f"📊 Coût moyen: ${avg:.4f}/client")
    
    print()

if __name__ == "__main__":
    main()

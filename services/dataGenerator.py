# services/data_generator.py
import json
import random
from datetime import datetime, timedelta
import os
from typing import List, Dict, Optional
from config.dbConfig import DATA_CONFIG

class FinancialDataGenerator:
    def __init__(self, seed: Optional[int] = None):
        # Optional deterministic seed for reproducible datasets (useful for tests)
        if seed is not None:
            random.seed(seed)

        self.categories = ["Food", "Shopping", "Rent", "Salary", "Utilities", "Entertainment", "Travel", "Others"]
        self.merchant_patterns = {
            "Food": ["Swiggy", "Zomato", "McDonald's", "Domino's", "Local Restaurant"],
            "Shopping": ["Amazon", "Flipkart", "Myntra", "Shopping Mall"],
            "Rent": ["Landlord", "Property Manager"],
            "Salary": ["Company XYZ", "Employer Corp"],
            "Utilities": ["Electricity Co", "Internet Provider", "Water Dept"],
            "Entertainment": ["Netflix", "Movie Theater", "Concert"],
            "Travel": ["Uber", "IRCTC", "Hotel Booking"],
            "Others": ["ATM", "Bank Transfer", "Friend"]
        }

    def generate_description(self, category: str, txn_type: str) -> str:
        """Generate realistic transaction description"""
        if txn_type == "Credit" and category == "Salary":
            return f"Salary credit from {random.choice(self.merchant_patterns['Salary'])}"
        elif txn_type == "Credit":
            return f"Refund from {random.choice(['Amazon', 'Swiggy', 'Utility'])}"
        else:
            payment_methods = ["UPI payment to", "Card payment at", "Online payment to", "Cash at"]
            return f"{random.choice(payment_methods)} {random.choice(self.merchant_patterns[category])}"

    def _get_amount_for_category(self, category: str) -> int:
        """Get realistic amount ranges for categories"""
        ranges = {
            "Food": (50, 1500),
            "Shopping": (100, 5000),
            "Rent": (8000, 20000),
            "Utilities": (500, 3000),
            "Entertainment": (200, 2000),
            "Travel": (1000, 10000),
            "Others": (50, 2000)
        }
        min_amt, max_amt = ranges.get(category, (50, 2000))
        return random.randint(min_amt, max_amt)

    def _infer_method_from_description(self, description: str, txn_type: str) -> str:
        """Infer a simple 'method' value to make filtering easier."""
        d = description.lower()
        if 'upi' in d:
            return "UPI"
        if 'card' in d:
            return "Card"
        if 'online' in d:
            return "Online"
        if 'cash' in d:
            return "Cash"
        if txn_type == "Credit" and 'refund' in d:
            return "Refund"
        return "Other"

    def generate_transactions(self) -> List[Dict]:
        """
        Generate synthetic financial transactions for multiple users.
        Ensures transactions per user are chronological so balances are correct.
        """
        transactions: List[Dict] = []
        base_txn_id = 1000

        for user_idx in range(1, DATA_CONFIG.num_users + 1):
            user_id = f"user_{user_idx}"
            # starting balance for this user (will be updated chronologically)
            balance = random.randint(20000, 50000)
            txn_count = random.randint(DATA_CONFIG.min_transactions, DATA_CONFIG.max_transactions)

            # Generate a list of random days_ago and then sort to ensure chronological order
            days_ago_list = [random.randint(1, 180) for _ in range(txn_count)]
            days_ago_list.sort(reverse=True)  # largest days_ago -> oldest date -> iterate oldest->newest

            for days_ago in days_ago_list:
                base_txn_id += 1
                date_str = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

                # Determine transaction type and category
                if random.random() < 0.15:  # ~15% credits
                    txn_type = "Credit"
                    category = "Salary" if random.random() < 0.7 else "Others"
                    amount = random.randint(2000, 15000) if category == "Salary" else random.randint(500, 2000)
                else:
                    txn_type = "Debit"
                    category = random.choice([c for c in self.categories if c != "Salary"])
                    amount = self._get_amount_for_category(category)

                description = self.generate_description(category, txn_type)
                method = self._infer_method_from_description(description, txn_type)

                # Update balance chronologically
                balance += amount if txn_type == "Credit" else -amount

                transaction = {
                    "id": f"txn_{base_txn_id}",
                    "userId": user_id,
                    "date": date_str,
                    "description": description,
                    "amount": amount,
                    "type": txn_type,
                    "category": category,
                    "method": method,
                    "balance": balance
                }
                transactions.append(transaction)

        return transactions

    def save_transactions(self, transactions: List[Dict]) -> str:
        """Save transactions to JSON file and return the path."""
        data_dir = os.path.dirname(DATA_CONFIG.data_path) or "data"
        os.makedirs(data_dir, exist_ok=True)
        with open(DATA_CONFIG.data_path, 'w', encoding='utf-8') as f:
            json.dump(transactions, f, indent=2, ensure_ascii=False)
        print(f"✅ Generated and saved {len(transactions)} transactions to {DATA_CONFIG.data_path}")
        return DATA_CONFIG.data_path


def generate_sample_data(seed: Optional[int] = None) -> List[Dict]:
    """Convenience function: generate and persist sample data. Returns transactions list."""
    generator = FinancialDataGenerator(seed=seed)
    transactions = generator.generate_transactions()
    generator.save_transactions(transactions)
    return transactions


if __name__ == "__main__":
    # Example: reproducible dataset for local dev/test
    generate_sample_data(seed=42)

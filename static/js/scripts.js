// Example JavaScript code to populate charts
document.addEventListener('DOMContentLoaded', function() {
    const ctx1 = document.getElementById('inventory-trends').getContext('2d');
    const ctx2 = document.getElementById('usage-patterns').getContext('2d');

    // Sample data for charts
    const inventoryTrendsChart = new Chart(ctx1, {
        type: 'line',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
            datasets: [{
                label: 'Inventory Trends',
                data: [30, 50, 70, 20, 90],
                borderColor: 'rgba(0, 123, 255, 1)',
                fill: false
            }]
        }
    });

    const usagePatternsChart = new Chart(ctx2, {
        type: 'pie',
        data: {
            labels: ['Medicines', 'Tools', 'Pharmaceuticals'],
            datasets: [{
                label: 'Usage Patterns',
                data: [300, 50, 150],
                backgroundColor: ['#ff6384', '#36a2eb', '#cc65fe']
            }]
        }
    });
});
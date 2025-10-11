// Gerenciamento do carrinho
let cart = JSON.parse(localStorage.getItem('ifoodCart')) || {
    restaurant_id: null,
    restaurant_name: '',
    items: [],
    total: 0
};

// Atualiza o carrinho no localStorage
function updateCart() {
    localStorage.setItem('ifoodCart', JSON.stringify(cart));
    updateCartUI();
}

// Adiciona um item ao carrinho
function addToCart(itemId, itemName, itemPrice, restaurantId, restaurantName) {
    // Verifica se o item é do mesmo restaurante
    if (cart.restaurant_id && cart.restaurant_id !== restaurantId) {
        if (confirm('Seu carrinho contém itens de outro restaurante. Deseja limpar o carrinho e adicionar este item?')) {
            clearCart();
        } else {
            return;
        }
    }
    
    // Define o restaurante se for o primeiro item
    if (!cart.restaurant_id) {
        cart.restaurant_id = restaurantId;
        cart.restaurant_name = restaurantName;
    }
    
    // Verifica se o item já está no carrinho
    const existingItem = cart.items.find(item => item.id === itemId);
    
    if (existingItem) {
        existingItem.quantity += 1;
        existingItem.subtotal = existingItem.quantity * existingItem.price;
    } else {
        cart.items.push({
            id: itemId,
            name: itemName,
            price: itemPrice,
            quantity: 1,
            subtotal: itemPrice
        });
    }
    
    // Atualiza o total
    calculateTotal();
    
    // Salva no localStorage
    updateCart();
    
    // Mostra mensagem de sucesso
    showToast('Item adicionado ao carrinho!');
}

// Calcula o total do carrinho
function calculateTotal() {
    cart.total = cart.items.reduce((total, item) => total + item.subtotal, 0);
}

// Remove um item do carrinho
function removeFromCart(itemId) {
    cart.items = cart.items.filter(item => item.id !== itemId);
    
    // Se o carrinho ficar vazio, limpa as informações do restaurante
    if (cart.items.length === 0) {
        cart.restaurant_id = null;
        cart.restaurant_name = '';
    }
    
    // Atualiza o total
    calculateTotal();
    
    // Salva no localStorage
    updateCart();
}

// Atualiza a quantidade de um item no carrinho
function updateItemQuantity(itemId, quantity) {
    const item = cart.items.find(item => item.id === itemId);
    
    if (item) {
        if (quantity <= 0) {
            removeFromCart(itemId);
            return;
        }
        
        item.quantity = quantity;
        item.subtotal = item.quantity * item.price;
        
        // Atualiza o total
        calculateTotal();
        
        // Salva no localStorage
        updateCart();
    }
}

// Limpa o carrinho
function clearCart() {
    cart = {
        restaurant_id: null,
        restaurant_name: '',
        items: [],
        total: 0
    };
    
    // Salva no localStorage
    updateCart();
}

// Atualiza a interface do carrinho
function updateCartUI() {
    const cartItemsElement = document.getElementById('cart-items');
    const cartTotalElement = document.getElementById('cart-total');
    const cartEmptyElement = document.getElementById('cart-empty');
    const cartContentElement = document.getElementById('cart-content');
    const restaurantNameElement = document.getElementById('restaurant-name');
    
    if (!cartItemsElement) return; // Não estamos na página do carrinho
    
    if (cart.items.length === 0) {
        cartEmptyElement.classList.remove('d-none');
        cartContentElement.classList.add('d-none');
        return;
    }
    
    cartEmptyElement.classList.add('d-none');
    cartContentElement.classList.remove('d-none');
    
    // Atualiza o nome do restaurante
    if (restaurantNameElement) {
        restaurantNameElement.textContent = cart.restaurant_name;
    }
    
    // Limpa os itens atuais
    cartItemsElement.innerHTML = '';
    
    // Adiciona os itens do carrinho
    cart.items.forEach(item => {
        const itemElement = document.createElement('div');
        itemElement.className = 'cart-item d-flex justify-content-between align-items-center';
        itemElement.innerHTML = `
            <div>
                <h6 class="mb-0">${item.name}</h6>
                <div class="text-muted">R$ ${item.price.toFixed(2)}</div>
            </div>
            <div class="d-flex align-items-center">
                <button class="btn btn-sm btn-outline-secondary me-2" onclick="updateItemQuantity('${item.id}', ${item.quantity - 1})">-</button>
                <span>${item.quantity}</span>
                <button class="btn btn-sm btn-outline-secondary ms-2" onclick="updateItemQuantity('${item.id}', ${item.quantity + 1})">+</button>
                <button class="btn btn-sm btn-outline-danger ms-3" onclick="removeFromCart('${item.id}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        cartItemsElement.appendChild(itemElement);
    });
    
    // Atualiza o total
    if (cartTotalElement) {
        cartTotalElement.textContent = `R$ ${cart.total.toFixed(2)}`;
    }
}

// Finaliza o pedido
function checkout() {
    if (cart.items.length === 0) {
        showToast('Seu carrinho está vazio!', 'danger');
        return;
    }
    
    // Envia o pedido para o servidor
    fetch('/checkout', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            restaurant_id: cart.restaurant_id,
            items: cart.items,
            total: cart.total
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Limpa o carrinho
            clearCart();
            
            // Redireciona para a página de pedidos
            window.location.href = '/orders';
        } else {
            showToast('Erro ao finalizar o pedido. Tente novamente.', 'danger');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        showToast('Erro ao finalizar o pedido. Tente novamente.', 'danger');
    });
}

// Exibe um toast de notificação
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container');
    
    if (!toastContainer) {
        // Cria o container de toasts se não existir
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '5';
        document.body.appendChild(container);
    }
    
    const toastId = `toast-${Date.now()}`;
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.id = toastId;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    document.getElementById('toast-container').appendChild(toast);
    
    const toastElement = new bootstrap.Toast(document.getElementById(toastId), {
        autohide: true,
        delay: 3000
    });
    
    toastElement.show();
}

// Inicializa a página
document.addEventListener('DOMContentLoaded', function() {
    // Atualiza a interface do carrinho se estivermos na página do carrinho
    updateCartUI();
    
    // Adiciona listeners para os botões de adicionar ao carrinho
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.getAttribute('data-item-id');
            const itemName = this.getAttribute('data-item-name');
            const itemPrice = parseFloat(this.getAttribute('data-item-price'));
            const restaurantId = this.getAttribute('data-restaurant-id');
            const restaurantName = this.getAttribute('data-restaurant-name');
            
            addToCart(itemId, itemName, itemPrice, restaurantId, restaurantName);
        });
    });
    
    // Adiciona listener para o botão de finalizar pedido
    const checkoutButton = document.getElementById('checkout-button');
    
    if (checkoutButton) {
        checkoutButton.addEventListener('click', checkout);
    }
});
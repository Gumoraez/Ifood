// Gerenciamento do carrinho
let cart = JSON.parse(localStorage.getItem('foodDeliveryCart')) || {
  items: [],
  restaurant_id: null,
  restaurant_name: '',
  total: 0
};

// Atualiza o carrinho no localStorage
function updateCart() {
  localStorage.setItem('foodDeliveryCart', JSON.stringify(cart));
  updateCartUI();
}

// Adiciona um item ao carrinho
function addToCart(itemId, itemName, itemPrice, restaurantId, restaurantName) {
  itemPrice = parseFloat(itemPrice);
  if (isNaN(itemPrice)) {
    alert('Preço inválido para o item.');
    return;
  }

  // Se já existe carrinho de outro restaurante, confirmar limpeza
  if (cart.restaurant_id && cart.restaurant_id !== restaurantId) {
    if (confirm('Seu carrinho contém itens de outro restaurante. Deseja limpar o carrinho e adicionar este item?')) {
      clearCart();
    } else {
      return;
    }
  }

  // Definir restaurante do carrinho
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

  // Recalcula total
  cart.total = cart.items.reduce((total, item) => total + item.subtotal, 0);

  updateCart();
  showToast('Item adicionado ao carrinho!');
}

// Remove um item do carrinho
function removeFromCart(itemId) {
  cart.items = cart.items.filter(item => item.id !== itemId);

  // Se o carrinho ficar vazio, limpa as informações do restaurante
  if (cart.items.length === 0) {
    cart.restaurant_id = null;
    cart.restaurant_name = '';
  }

  // Recalcula total
  cart.total = cart.items.reduce((total, item) => total + item.subtotal, 0);

  updateCart();
}

// Atualiza a quantidade de um item no carrinho
function updateItemQuantity(itemId, newQuantity) {
  newQuantity = parseInt(newQuantity);
  if (isNaN(newQuantity) || newQuantity < 1) {
    removeFromCart(itemId);
    return;
  }

  const item = cart.items.find(item => item.id === itemId);
  if (!item) return;

  item.quantity = newQuantity;
  item.subtotal = item.quantity * item.price;

  // Recalcula total
  cart.total = cart.items.reduce((total, item) => total + item.subtotal, 0);

  updateCart();
}

// Limpa o carrinho
function clearCart() {
  cart = {
    items: [],
    restaurant_id: null,
    restaurant_name: '',
    total: 0
  };
  updateCart();
}

// Atualiza a interface do carrinho
function updateCartUI() {
  const cartItemsElement = document.getElementById('cart-items');
  const cartTotalElement = document.getElementById('cart-total');
  const cartEmptyElement = document.getElementById('cart-empty');
  const cartContentElement = document.getElementById('cart-content');
  const restaurantNameElement = document.getElementById('restaurant-name');

  if (!cartItemsElement) return; // Não estamos na página do carrinho/restaurante

  if (cart.items.length === 0) {
    if (cartEmptyElement) cartEmptyElement.classList.remove('d-none');
    if (cartContentElement) cartContentElement.classList.add('d-none');
    if (cartTotalElement) cartTotalElement.textContent = 'R$ 0.00';
    if (restaurantNameElement) restaurantNameElement.textContent = cart.restaurant_name || '';
    return;
  }

  if (cartEmptyElement) cartEmptyElement.classList.add('d-none');
  if (cartContentElement) cartContentElement.classList.remove('d-none');
  if (restaurantNameElement) restaurantNameElement.textContent = cart.restaurant_name;

  // Renderizar itens
  cartItemsElement.innerHTML = '';
  cart.items.forEach(item => {
    const itemElement = document.createElement('div');
    itemElement.className = 'cart-item d-flex justify-content-between align-items-center';
    itemElement.innerHTML = `
      <div>
        <strong>${item.name}</strong>
        <div class="text-muted small">R$ ${item.price.toFixed(2)} x </div>
      </div>
      <div class="d-flex align-items-center">
        <input type="number" min="1" value="${item.quantity}" class="form-control form-control-sm" style="width: 70px;" onchange="updateItemQuantity('${item.id}', this.value)">
        <span class="ms-3">R$ ${item.subtotal.toFixed(2)}</span>
        <button class="btn btn-sm btn-outline-danger ms-3" onclick="removeFromCart('${item.id}')">
          <i class="fas fa-trash"></i>
        </button>
      </div>
    `;
    cartItemsElement.appendChild(itemElement);
  });

  // Total
  if (cartTotalElement) {
    cartTotalElement.textContent = `R$ ${cart.total.toFixed(2)}`;
  }
}

// Toast simples
function showToast(message, type = 'success') {
  const alertDiv = document.createElement('div');
  alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
  alertDiv.style.top = '80px';
  alertDiv.style.right = '20px';
  alertDiv.style.zIndex = '1050';
  alertDiv.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;
  document.body.appendChild(alertDiv);
  setTimeout(() => {
    alertDiv.classList.remove('show');
    alertDiv.remove();
  }, 2500);
}

// Checkout
function checkout() {
  if (cart.items.length === 0) {
    showToast('Seu carrinho está vazio!', 'danger');
    return;
  }

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
      showToast('Pedido realizado com sucesso!');
      // Limpa o carrinho
      clearCart();
      // Redireciona para Meus Pedidos
      window.location.href = '/orders';
    } else {
      showToast(data.message || 'Erro ao realizar pedido', 'danger');
    }
  })
  .catch(error => {
    console.error(error);
    showToast('Erro ao realizar pedido', 'danger');
  });
}

// Inicialização ao carregar página
document.addEventListener('DOMContentLoaded', function() {
  // Atualiza a interface do carrinho se estivermos na página do carrinho
  updateCartUI();

  // Adiciona listeners para os botões de adicionar ao carrinho
  const addToCartButtons = document.querySelectorAll('.add-to-cart');
  if (addToCartButtons && addToCartButtons.length) {
    addToCartButtons.forEach(button => {
      button.addEventListener('click', function() {
        const itemId = this.getAttribute('data-item-id');
        const itemName = this.getAttribute('data-item-name');
        const itemPrice = this.getAttribute('data-item-price');
        const restaurantId = this.getAttribute('data-restaurant-id');
        const restaurantName = this.getAttribute('data-restaurant-name');
        addToCart(itemId, itemName, itemPrice, restaurantId, restaurantName);
      });
    });
  }

  // Botão de checkout
  const checkoutButton = document.getElementById('checkout-button');
  if (checkoutButton) {
    checkoutButton.addEventListener('click', checkout);
  }
});
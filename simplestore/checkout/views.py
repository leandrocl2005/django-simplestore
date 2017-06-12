from django.shortcuts import redirect
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.views.generic import DetailView, TemplateView
from simplestore.cart.mixins import get_cart
from .forms import CustomerOrderForm, ShippingAddressForm, DeliveryMethodForm
from .models.order import Order


class CheckoutOrderCreateView(TemplateView):
    template_name = 'checkout_index.html'

    def dispatch(self, request, *args, **kwargs):
        self.cart = get_cart(self.request)
        if not self.cart:
            return redirect('cart:index')

        self.forms = self.get_order_forms()

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not all(form.is_valid() for form in self.forms.values()):
            return self.get(request, *args, **kwargs)

        order = self.create_order()

        self.clean_session()
        self.send_email_confirmation(order)

        return redirect(order.get_absolute_url())

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            **self.forms,
            'cart': self.cart,
        }

    def get_order_forms(self):
        request = self.request
        data = request.POST if self.request.method == 'POST' else None
        return {
            'customer_order_form': CustomerOrderForm(data),
            'shipping_address_form': ShippingAddressForm(data),
            'delivery_method_form': DeliveryMethodForm(data),
        }

    def create_order(self):
        forms = self.forms

        order = forms['customer_order_form'].save(commit=False)
        shipping_address = forms['shipping_address_form'].save()
        delivery_method = forms['delivery_method_form'].cleaned_data['delivery_method']

        order.cart = self.cart
        order.shipping_address = shipping_address
        order.delivery_method = delivery_method

        if self.request.user.is_authenticated():
            order.user = self.request.user

        order.save()
        order.create_order_items()

        return order

    def clean_session(self):
        """
        Clean Cart session for authenticated user when order is processed
        """
        try:
            del self.request.session['user_cart']
        except KeyError:
            self.request.session.create()

    @staticmethod
    def send_email_confirmation(order):
        """
        Send email with order details 
        """
        message = render_to_string("emails/order_conf.txt", {
            'order': order,
        })
        mail = EmailMessage(
            subject="Order confirmation",
            body=message,
            from_email='test@martinstastny.cz',
            to=['me@martinstastny.cz'],
            reply_to=['test@martinstastny.cz'],
        )
        mail.content_subtype = "html"
        mail.send()


class OrderConfirmationView(DetailView):
    model = Order
    template_name = "order_confirmation.html"

    def get_context_data(self, **kwargs):
        context_data = super(OrderConfirmationView, self).get_context_data()
        return context_data
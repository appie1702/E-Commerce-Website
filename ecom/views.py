from django.views.generic import CreateView, UpdateView, View, ListView, DeleteView, DetailView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from .forms import SignUpForm, CheckoutForm, CouponForm, RefundForm
from .models import Item, OrderItem, Order, Address, Coupon, Refund
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
import razorpay
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import random
import string


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


class LoginPage(SuccessMessageMixin, LoginView):
    template_name = 'ecom/ecom_login.html'
    success_message = "You are successfully logged in!"


class LogoutPage(LogoutView):
    def get_next_page(self):
        next_page = super(LogoutPage, self).get_next_page()
        messages.add_message(
            self.request, messages.SUCCESS,
            'You successfully logged out!'
        )
        return reverse('ecom:ecom_home')


class SignUpPage(CreateView):
    form_class = SignUpForm
    success_url = reverse_lazy('ecom:ecom_login')
    template_name = 'ecom/ecom_signup.html'


class HomePageView(ListView):
    model = Item
    template_name = 'ecom/ecom_home.html'
    paginate_by = 10

    def post(self, request, *args, **kwargs):
        searched = request.POST.get('searched')
        searched_items = self.get_queryset().filter(title__icontains=searched)
        return render(request, self.template_name, {'object_list': searched_items})


class ItemDetailView(DetailView):
    model = Item
    template_name = 'ecom/ecom_detail.html'


@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created_at = OrderItem.objects.get_or_create(item=item, user=request.user, ordered=False)
    order_q = Order.objects.filter(user=request.user, ordered=False)
    if order_q.exists():
        order = order_q[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item.save()
            return redirect("ecom:ecom_cart")
        else:
            order.items.add(order_item)
            order_item.save()
            order.save()
            messages.info(request, "The item has been added to your cart.")
            return redirect("ecom:ecom_cart")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        order.save()
        messages.info(request, "The item has been added to your cart.")
        return redirect("ecom:ecom_cart")


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_q = Order.objects.filter(user=request.user, ordered=False)
    if order_q.exists():
        order = order_q[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(item=item, user=request.user, ordered=False)[0]
            order.items.remove(order_item)
            order_item.delete()
            order.save()
            messages.info(request, "This item has been removed from your cart.")
            redirect("ecom:ecom_cart")
        else:
            messages.info(request, "This item was not in your cart.")
            return redirect("ecom:ecom_cart")
    else:
        messages.info(request, "You don't have any items in your cart.")
        return redirect("ecom:ecom_cart")
    return redirect("ecom:ecom_cart")


def increase_quantity(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_q = Order.objects.filter(user=request.user, ordered=False)
    if order_q.exists():
        order = order_q[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(item=item, user=request.user, ordered=False)[0]

            order_item.quantity += 1
            order_item.save()
            order.save()
            messages.info(request, "The item's quantity has been updated.")
            return redirect("ecom:ecom_cart")
        else:
            messages.info(request, "The item was not in your cart.")
            return redirect("ecom:ecom_cart")
    else:
        messages.info(request, "You don't have any items in your cart.")
        return redirect("ecom:ecom_cart")


@login_required
def decrease_quantity(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_q = Order.objects.filter(user=request.user, ordered=False)
    if order_q.exists():
        order = order_q[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(item=item, user=request.user, ordered=False)[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
                order.save()
                messages.info(request, "This item's quantity has been updated.")
                return redirect("ecom:ecom_cart")
            else:
                order.items.remove(order_item)
                order_item.delete()
                order.save()
                messages.info(request, "This item has been removed from your cart.")
                return redirect("ecom:ecom_cart")
        else:
            messages.info(request, "This item was not in your cart.")
            return redirect("ecom:ecom_cart")
    else:
        messages.info(request, "You don't have any items in your cart.")
        return redirect("ecom:ecom_cart")


class CartView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'ecom/ecom_cart_items.html', context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You have no items in your cart")
            return redirect("ecom:ecom_home")


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid


class CheckOutView(LoginRequiredMixin, View):
    login_url = '/login'

    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            # order_items_count = Order.objects.filter(user=self.request.user, ordered=False)[0].items.count()

            form = CheckoutForm()
            context = {
                'form': form,
                'order': order,
                'couponform': CouponForm(),
                'DISPLAY_COUPON_FORM': True
            }

            shipping_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='S',
                default=True
            )
            if shipping_address_qs.exists():
                context.update(
                    {'default_shipping_address': shipping_address_qs[0]})

            billing_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='B',
                default=True
            )
            if billing_address_qs.exists():
                context.update(
                    {'default_billing_address': billing_address_qs[0]})

            return render(self.request, "ecom/ecom_checkout.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You don't have any items in your cart.")
            return redirect("ecom:ecom_home")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                use_default_shipping = form.cleaned_data.get('use_default_shipping')
                print(use_default_shipping)
                if use_default_shipping:
                    default_address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='S',
                        default=True
                    )
                    if default_address_qs.exists():
                        shipping_address = default_address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default shipping address available")
                        return redirect('ecom:ecom_checkout')
                else:
                    shipping_address_line1 = form.cleaned_data.get('shipping_address_line1')
                    shipping_address_line2 = form.cleaned_data.get('shipping_address_line2')
                    shipping_country = form.cleaned_data.get('shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')

                    if is_valid_form([shipping_address_line1, shipping_address_line2, shipping_country, shipping_zip]):
                        shipping_address = Address(
                            user=self.request.user,
                            address_line1=shipping_address_line1,
                            address_line2=shipping_address_line2,
                            country=shipping_country,
                            zip=shipping_zip,
                            address_type='S'
                        )
                        shipping_address.save()
                        order.shipping_address = shipping_address

                        set_default_shipping = form.cleaned_data.get(
                            'set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()
                        order.save()
                    else:
                        messages.info(self.request, "You have not filled the required shipping address details")
                        return redirect("ecom:ecom_checkout")
                use_default_billing = form.cleaned_data.get('use_default_billing')
                same_billing_address = form.cleaned_data.get('same_billing_address')

                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()
                elif use_default_billing:
                    default_address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='B',
                        default=True
                    )
                    if default_address_qs.exists():
                        billing_address = default_address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(self.request, "No default shipping address available")
                        return redirect('ecom:ecom_checkout')
                else:
                    billing_address_line1 = form.cleaned_data.get('billing_address_line1')
                    billing_address_line2 = form.cleaned_data.get('billing_address_line2')
                    billing_country = form.cleaned_data.get('billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')

                    if is_valid_form([billing_address_line1, billing_address_line2, billing_country, billing_zip]):
                        billing_address = Address(
                            user=self.request.user,
                            address_line1=billing_address_line1,
                            address_line2=billing_address_line2,
                            country=billing_country,
                            zip=billing_zip,
                            address_type='S'
                        )
                        billing_address.save()

                        set_default_billing = form.cleaned_data.get(
                            'set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()

                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(self.request, "You have not filled the required shipping address details")

                payment_option = form.cleaned_data.get('payment_options')

                if payment_option == "POD":
                    order.ordered = True
                    order.ref_code = create_ref_code()
                    order_items = OrderItem.objects.all()
                    order_items.update(ordered=True)
                    for order_item in order_items:
                        order_item.save()
                    order.save()
                    messages.info(self.request, "Thank You! Your order has been placed.")
                    return redirect("ecom:ecom_home")
                else:
                    amount = int(order.get_total() * 100)
                    return redirect("ecom:handle_payment", amount=amount)
            else:
                messages.info(self.request, "Form was not valid")
                return redirect("ecom:ecom_checkout")
        except ObjectDoesNotExist:
            messages.info(self.request, "You have no items in your cart")
            return redirect("ecom:ecom_checkout")


@login_required
def buy_now(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created_at = OrderItem.objects.get_or_create(item=item, user=request.user, ordered=False)
    order_q = Order.objects.filter(user=request.user, ordered=False)
    if order_q.exists():
        order = order_q[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item.save()
            return redirect("ecom:ecom_checkout")
        else:
            order.items.add(order_item)
            order_item.save()
            order.save()
            return redirect("ecom:ecom_checkout")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        order.save()
        return redirect("ecom:ecom_checkout")


@login_required
def handle_payment(request, amount):
    if request.method == "GET":
        order = Order.objects.get(user=request.user, ordered=False)
        if order.billing_address:
            return render(request, "ecom/online_pay.html", {'amount': amount})
        else:
            messages.info(request, "You have not added any billing address.")
            return redirect("ecom:ecom_checkout")
    if request.method == "POST":
        client = razorpay.Client(auth=("rzp_test_OQF0zUX3v90kI6", "aiXwvXSIkjkHdPKwJoqaVLzX"))
        amount = int(amount)
        currency = "INR"
        receipt = "receipt#1"
        payment_capture = "1"
        payment = client.order.create({
            'amount': amount,
            'currency': currency,
            'receipt': receipt,
            'payment_capture': payment_capture
        })
    return render(request, "ecom/online_pay.html", {'amount': amount})


@csrf_exempt
def success_payment(request):
    try:
        order = Order.objects.filter(user=request.user, ordered=False)[0]
        order.ordered = True
        order.paid = True
        order.ref_code = create_ref_code()
        order_items = OrderItem.objects.all()
        order_items.update(ordered=True)
        for order_item in order_items:
            order_item.save()
        order.save()
        return render(request, "ecom/payment_success.html")
    except:
        messages.info(request, "Some error occured. But Don't worry, transaction was successful.")
        return redirect("ecom:ecom_home")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    user=self.request.user, ordered=False)
                try:
                    coupon = Coupon.objects.get(code=code)
                    if not order.coupon == coupon:
                        order.coupon = coupon
                        order.save()
                    else:
                        messages.info(self.request, "This coupon-code has already been applied.")
                        return redirect("ecom:ecom_checkout")
                    messages.success(self.request, "Successfully added coupon")
                    return redirect("ecom:ecom_checkout")
                except ObjectDoesNotExist:
                    messages.info(self.request, "This coupon does not exist.")
                    return redirect("ecom:ecom_checkout")
            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect("ecom:ecom_checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "ecom/ecom_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            # edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your request has been received. We will be in touch with you shortly.")
                return redirect("ecom:request_refund")

            except ObjectDoesNotExist:
                messages.info(self.request,
                              "Either this order does not exist or the Reference code entered is incorrect or invalid.")
                return redirect("ecom:request_refund")

import razorpay
from datetime import datetime
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Booking

class CreateOrderView(APIView):
    def post(self, request):
        data = request.data
        amount = int(data.get('amount', 0))
        pay_mode = data.get('pay_mode', 'secure')
        
        # =============================================================
        # FIX: Convert 12-Hour AM/PM String to Django Datetime Object
        # =============================================================
        raw_date_str = data.get('date') # e.g., "2026-06-15 2:30 PM"
        try:
            # Parses "2:30 PM" or "14:30" formats into standard database format
            if "AM" in raw_date_str or "PM" in raw_date_str:
                formatted_datetime = datetime.strptime(raw_date_str, '%Y-%m-%d %I:%M %p')
            else:
                formatted_datetime = datetime.strptime(raw_date_str, '%Y-%m-%d %H:%M')
        except Exception as e:
            print(f"Datetime Parsing Error: {str(e)}")
            return Response({
                'success': False, 
                'error': f"Invalid date/time format received: {raw_date_str}"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # ==========================================
            # PATH A: PAY ON SPOT (BYPASS GATEWAY)
            # ==========================================
            if pay_mode == 'spot':
                Booking.objects.create(
                    name=data.get('name'),
                    phone=data.get('phone'),
                    email=data.get('email'),
                    package_name=data.get('package'),
                    booking_date=formatted_datetime, # Uses clean datetime object
                    amount=0, 
                    status='Confirmed - Pay on Spot'
                )
                
                return Response({
                    'success': True,
                    'payment_required': False, 
                    'message': 'Booking confirmed for Pay on Spot.'
                }, status=status.HTTP_200_OK)

            # ==========================================
            # PATH B: SECURE SPOT (REQUIRES RAZORPAY)
            # ==========================================
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            order_amount = amount * 100 
            order_currency = 'INR'
            order_receipt = f"asx_{data.get('phone')}"

            razorpay_order = client.order.create(dict(
                amount=order_amount,
                currency=order_currency,
                receipt=order_receipt,
                payment_capture='1'
            ))

            Booking.objects.create(
                name=data.get('name'),
                phone=data.get('phone'),
                email=data.get('email'),
                package_name=data.get('package'),
                booking_date=formatted_datetime, # Uses clean datetime object
                amount=amount, 
                razorpay_order_id=razorpay_order['id'],
                status='Pending'
            )

            return Response({
                'success': True,
                'payment_required': True,
                'order_id': razorpay_order['id'],
                'amount': order_amount,
                'currency': order_currency
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Backend Error: {str(e)}") 
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
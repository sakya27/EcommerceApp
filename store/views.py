from django.shortcuts import render
from django.http import JsonResponse
import json
import datetime
from .models import * 
from .utils import cookieCart, cartData, guestOrder
import openai
import os
import math

from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain import PromptTemplate, LLMChain
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter,NLTKTextSplitter
from ecommerce.settings import DATABASES

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

import sqlite3

def get_product_descriptions():
    # Connect to the SQLite database (replace 'your_database.db' with your actual database file)
    conn = sqlite3.connect(DATABASES['default']['NAME'])
    cursor = conn.cursor()

    try:
        # Execute a SELECT query to fetch all columns from the specified table
        cursor.execute(f"SELECT description FROM store_product;")

        # Fetch all rows from the result set
        rows = cursor.fetchall()
        desp=""
        for row in rows:
            desp=row[0]+"\n"



    except sqlite3.Error as e:
        print("SQLite Error:", e)

    finally:
        # Close the connection
        conn.close()
        return desp

# Replace 'your_table_name' with the actual name of your table

def store(request):
    data = cartData(request)

    cartItems = data['cartItems']
    order = data['order']
    items = data['items']

    products = Product.objects.all()
    context = {'products':products, 'cartItems':cartItems}
    return render(request, 'store/store.html', context)


def cart(request):
    data = cartData(request)

    cartItems = data['cartItems']
    order = data['order']
    items = data['items']

    context = {'items':items, 'order':order, 'cartItems':cartItems}
    return render(request, 'store/cart.html', context)

def checkout(request):
    data = cartData(request)

    cartItems = data['cartItems']
    order = data['order']
    items = data['items']

    context = {'items':items, 'order':order, 'cartItems':cartItems}
    return render(request, 'store/checkout.html', context)


def product_detail(request, product_id):

    print(product_id)
    product = Product.objects.get(id=product_id)
    return render(request, 'store/product_detail.html', {'product': product})

def save_embeddings(captions):

    text_splitter = NLTKTextSplitter(chunk_size=500)
    texts = text_splitter.split_text(captions)

    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    db = FAISS.from_texts(texts, embeddings)
    return db



def llm_answer(question, description):

    faiss_db = save_embeddings(description)
    docs = faiss_db.similarity_search(question, k=1)
    data = docs[0].page_content
    template = """\
    Answer a question when the question and the relevant data is given.\
    Relevant data: {data}\
    Question: {question}\
    Answer:
    """
    try:
        prompt = PromptTemplate(template=template, input_variables=["data", "question"])
        llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model='gpt-3.5-turbo-16k-0613')
        # llm = PALM()
        llm_chain = LLMChain(prompt=prompt, llm=llm)
        output = llm_chain.run({'data':data, 'question':question})
        #timestamp = int(docs[0].metadata['start'])

        return 'success', output
    except:
        return 'fail',''

def chat_window(request):
    return render(request, 'store/chat.html')


def chat_with_product(request):

    context = get_product_descriptions()

    prompt = request.POST.get('prompt')
    status,response = llm_answer(prompt,context)
    '''print(status)
    print(response)'''
    context = {'response': response}
    return JsonResponse(context)

def updateItem(request):
    data = json.loads(request.body)
    productId = data['productId']
    action = data['action']
    print('Action:', action)
    print('Product:', productId)

    customer = request.user.customer
    product = Product.objects.get(id=productId)
    order, created = Order.objects.get_or_create(customer=customer, complete=False)

    orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

    if action == 'add':
        orderItem.quantity = (orderItem.quantity + 1)
    elif action == 'remove':
        orderItem.quantity = (orderItem.quantity - 1)

    orderItem.save()

    if orderItem.quantity <= 0:
        orderItem.delete()

    if action == 'add':
        return JsonResponse('Item was added', safe=False)
    elif action == 'remove':
        return JsonResponse('Item was removed', safe=False)


def processOrder(request):
    transaction_id = datetime.datetime.now().timestamp()
    data = json.loads(request.body)

    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
    else:
        customer, order = guestOrder(request, data)

    total = float(data['form']['total'])
    order.transaction_id = transaction_id

    if total == order.get_cart_total:
        order.complete = True
    order.save()

    if order.shipping == True:
        ShippingAddress.objects.create(
        customer=customer,
        order=order,
        address=data['shipping']['address'],
        city=data['shipping']['city'],
        state=data['shipping']['state'],
        zipcode=data['shipping']['zipcode'],
        )

    return JsonResponse('Payment submitted..', safe=False)


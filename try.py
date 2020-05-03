from flask import Flask, render_template, request, jsonify
import pandas as pd
import time
#IMPORTING EXPLAINATION GENERATOR MODULE
import expgen

#IMPORTING BLOCKCHAIN REQUIREMENTS
import datetime
import hashlib
import json
import requests
from uuid import uuid4
from urllib.parse import urlparse

# BUILDING THE BLOCKCHAIN

class Blockchain:   

    def __init__(self):
        self.chain = []
        self.transactions = ['Genesis Block', 'This block will not contain any transactions.', 
        'The hash of the previous block will be zero which is obvious.', 
        'The transactions will contain all the feauteres that the initial file will have plus the explanations that will be generated by the modal']
        self.user_list = [0]
        self.create_block(proof = 1, previous_hash = '0')
        self.node = set()

    def create_block(self, proof, previous_hash):
        block = {'index': len(self.chain) + 1,
                 'timestamp': str(datetime.datetime.now()),
                 'proof': proof,
                 'previous_hash': previous_hash,
                 'user_list': self.user_list,
                 'transactions': self.transactions}
        self.user_list = []
        self.transactions = []
        self.chain.append(block)
        return block

    def get_previous_block(self):
        return self.chain[-1]

    def proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False
        while check_proof is False:
            hash_operation = hashlib.sha256(str(new_proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] == '0000':
                check_proof = True
            else:
                new_proof += 1
        return new_proof
    
    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys = True).encode()
        return hashlib.sha256(encoded_block).hexdigest()
    
    def is_chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1
        while block_index < len(chain):
            block = chain[block_index]
            if block['previous_hash'] != self.hash(previous_block):
                return False
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] != '0000':
                return False
            previous_block = block
            block_index += 1
        return True
    
    def add_transactions (self, user_list, dataDict):
        for x in user_list:
            self.user_list.append(x)

        for key, value in dataDict.items():
            self.transactions.append(dataDict[key])
        prev_block = self.get_previous_block()
        return prev_block['index'] + 1
    
    def add_node(self, address):
        parsed_url = urlparse(address)
        self.node.add(parsed_url.netloc)
        
    def replace_chain(self):
        network = self.node
        longest_chain = None
        max_length = len(self.chain)
        
        for node in network:
            response = request.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length & self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain
        if longest_chain:
            return True
        return False   

# CREATING WEBAPP

# CREATING THE BLOCKCHAIN
blockchain = Blockchain()

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

excelData = pd.DataFrame()
dataDict = ()
fileHeader = []
explaination_list = []
excelDataTranspose = pd.DataFrame()

@app.route('/data', methods=['GET', 'POST'])
def data():
    if request.method == 'POST':
        global excelData
        global dataDict
        file = request.form['upload-file']
        excelData = pd.read_excel(file)
        dataTranspose = excelData.T
        dataDict = dataTranspose.to_dict()   
        if not explaination_list:
            return (render_template('data.html', data=dataTranspose.to_html()))
        else:
            return (render_template('exp_error.html', explainations = explaination_list))

#HANDLING LEFTOVER TRANSACTIONS
@app.route('/clear_exp', methods=['GET','POST'])
def clear_exp():
    explaination_list.clear()
    return (render_template('index.html'))

#EXPLAINATIONS GENERATOR
@app.route('/explainations', methods=['GET', 'POST'])
def explainations():
    global explaination_list
    count = 0
    for ind in excelData.index:
        x = excelData.iloc[ind, 2:25].values
        y = excelData.iloc[ind, 1]
        explaination, pred_good = expgen.generate_exp1(x)
        if((pred_good>0.5 and y==1) or (pred_good<0.5 and y==0)): #correct observation
            count = count +1
        explaination_list.append(explaination)
    acc = count/(excelData.shape[0])
    print("Accuracy is ", acc)
    print("Shape", excelData.shape)
    return (render_template('explainations.html', explainations = explaination_list, excelData = excelData)), 200

#APPENDING EXPLAINATIONS AND DISPLAYING THE NEW DATA
@app.route('/data2', methods=['GET', 'POST'])
def data2():
    if request.method == 'POST':
        global excelData
        global explaination_list
        global excelDataTranspose
        print(len(explaination_list))
        print(len(excelData.index))
        excelData['Explanations'] = explaination_list
        explaination_list.clear()
        excelDataTranspose = excelData.T
        return (render_template('data2.html', data=excelDataTranspose.to_html()))

# REQUESTING BLOCK
@app.route('/request_block', methods=['GET', 'POST'])
def request_block():
    return render_template('request_block.html')

# GETTING SPECIFIC BLOCK
@app.route('/get_block', methods=['POST'])
def get_block():
    block_number = request.form['block_number']
    block_number = int(block_number)
    # GETTING ALL THE BLOCKS IN THE BLOCKCHAIN
    chain = blockchain.chain
    for block in chain:
        if block_number == block['index']:
            return render_template('get_block.html', block = block, message = "Block Found")
    return render_template('get_block.html', message = "Block Not Found")


#REQUESTING SPECIFIC USER
@app.route('/request_user', methods=['GET', 'POST'])
def request_user():
    return render_template('request_user.html')

#GETTING SPECIFIC USER
@app.route('/get_user', methods=['POST'])
def get_user():
    user_id = int(request.form['user_id'])
    all_user_instances = get_all_instances(user_id)
    chain = blockchain.chain
    user_all_details = []
    block_timestamps = []
    for block in chain:
        if compare_index(block['index'], all_user_instances):
            print("Returned List is", block['index'])
            a = block['transactions']
            for item in range(len(a)):
                # print(a[item], type(a[item]))
                if isinstance(a[item], dict):
                    for key, value in a[item].items(): #a[item] = transaction list
                        if key == "UserID":
                            if value == user_id:
                                print("User Found", key, value)
                                user_all_details.append(a[item])
                                block_timestamps.append(block['timestamp'])
    # for k in range(len(user_all_details)):
    #     for j in range(len(block_timestamps)):
    #         if k == j:
    #             print(block_timestamps[k], user_all_details[k])
    
    if user_all_details:
        return (render_template('get_user.html', message = "User Found in",
                                user_all_details = user_all_details,
                                block_timestamps = block_timestamps, 
                                len_user = len(user_all_details),
                                len_block = len(block_timestamps),
                                all_user_instances = all_user_instances,
                                len_all_user_instances = len(all_user_instances) ))
    return render_template('get_user.html', message = 'User Not Found in any block')

#TO CHECK BLOCK INDEX WITH ALL INSTANCES
def compare_index(block_index, all_user_instances):
    for key in all_user_instances:
        if block_index == key:
            return True


#FUNCTION TO RETRIEVE ALL THE BLOCKS WHICH CONTAIN THE SPECIFIC USER ID
def get_all_instances(user_id):
    chain = blockchain.chain
    all_user_instances = []
    for block in chain:
        user_list = block['user_list']
        for stored_user_id in user_list:
            if stored_user_id == user_id:
                all_user_instances.append(block['index'])
    print("User found in blocks", all_user_instances)
    return all_user_instances

#TESTING DATA
@app.route('/test')
def test():
    global excelData
    global dataDict
    for x in dataDict:
        print(x)
    return "All OK",200

#PARSING THE URLs
node_address = str(uuid4()).replace('-','')

# MINING A NEW BLOCK
@app.route('/mine_block', methods = ['GET'])
def mine_block():
    previous_block = blockchain.get_previous_block()
    previous_proof = previous_block['proof']
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)
    block = blockchain.create_block(proof, previous_hash)
    response = {'message': 'Congratulations, you just mined a block!',
                'index': block['index'],
                'timestamp': block['timestamp'],
                'proof': block['proof'],
                'previous_hash': block['previous_hash'],
                'user_list': block['user_list'],
                'transactions': block['transactions']}
    return  (render_template('mine_block.html', block=response)), 200


# GETTING THE FULL BLOCKCHAIN
@app.route('/get_chain', methods = ['GET'])
def get_chain():
    response = {'chain': blockchain.chain,
                'length': len(blockchain.chain)}
    return (render_template('get_chain.html', chains=response['chain'])), 200
  
#CHECKING IF THE BLOCKCHAIN IS VALID
@app.route('/is_valid', methods = ['GET'])
def is_valid():
    is_valid = blockchain.is_chain_valid(blockchain.chain)
    if is_valid:
        response = {'message': 'All good. The Blockchain is valid.'}
    else:
        response = {'message': 'Houston, we have a problem. The Blockchain is not valid.'}
    return jsonify(response), 200

@app.route('/add_transaction', methods = ['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        global dataDict
        global excelDataTranspose

        dataDict = excelDataTranspose.to_dict() 
        
        transaction_keys = []
        for x in dataDict:
            transaction_keys.append(x)

        user_list = [] #collecting user ids in the datadict
        for key,value in dataDict.items():
            for index, item in value.items():
                # print(index)
                if index == "UserID":
                    user_list.append(item)            

        if not all (key in dataDict for key in transaction_keys):
            return "Some keys are missing", 400
        index = blockchain.add_transactions(user_list, dataDict)
        response = {'message': f'This transaction will be added to block #{index}'}
        return (render_template('add_transaction.html', msg=response['message']))

@app.route('/connect_node', methods = ['POST'])
def connect_node():
    json = request.get_json()
    nodes = json.get("nodes")
    if nodes in json is None:
        return 'No Node', 400
    for node in nodes:
        blockchain.add_node(node)
    response = {'message': 'Nodes added successfully. The nodes in Blockchain are:',
                'total_nodes': list(blockchain.node)}
    return jsonify(response), 201
    
@app.route('/replace_chain', methods = ['GET'])
def replace_chain():
    is_chain_replaced = blockchain.replace_chain()
    if is_chain_replaced:
        response = {'message': 'Chain was replaced by the longest one',
                    'new_chain': blockchain.chain}
    else:
        response = {'message': 'All Good. Chain is the longest one',
                    'actual_chain': blockchain.chain}
    return jsonify(response), 200


if __name__ == '__main__':
    app.run(debug=True, port = 5001)
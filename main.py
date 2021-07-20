import os
import argparse
import model
import utils
import wandb
from tqdm import tqdm

import torch
import torch.nn as nn
from torchvision import transforms as T


def train_epoch(epoch, net, train_loader, val_loader , criterion, optimizer, scheduler, device):
    """
    Training logic for an epoch
    """
    train_loss = utils.AverageMeter("Epoch losses", ":.4e")
    train_acc1 = utils.AverageMeter("Train Acc@1", ":6.2f")
    train_acc5 = utils.AverageMeter("Train Acc@5", ":6.2f")
    net.train()

    for _, (inputs, targets) in enumerate(tqdm(train_loader)):
        inputs = inputs.to(device)
        targets = targets.to(device)

        # Forward pass
        outputs = net(inputs)
        loss = criterion(outputs, targets)
        acc1, acc5 = utils.accuracy(outputs, targets, topk=(1, 5))

        train_loss.update(loss.item(), inputs.size(0))
        train_acc1.update(acc1.item(), inputs.size(0))
        train_acc5.update(acc5.item(), inputs.size(0))

        # Backward and optimize
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        scheduler.step()


    # Validation model
    val_loss = utils.AverageMeter("Val losses", ":.4e")
    val_acc1 = utils.AverageMeter("Val Acc@1", ":6.2f")
    val_acc5 = utils.AverageMeter("Val Acc@5", ":6.2f")
    progress = utils.ProgressMeter(
        num_batches = len(val_loader),
        meters = [val_loss, val_acc1, val_acc5],
        prefix = 'Epoch: {} '.format(epoch + 1),
        batch_info = " Iter"
    )
    net.eval()

    for it, (inputs, targets) in enumerate(val_loader):
        inputs = inputs.to(device)
        targets = targets.to(device)

        # Forward pass
        with torch.no_grad():
            outputs = net(inputs)
            loss = criterion(outputs, targets)
            acc1, acc5 = utils.accuracy(outputs, targets, topk=(1, 5))
        val_loss.update(loss.item(), inputs.size(0))
        val_acc1.update(acc1.item(), inputs.size(0))
        val_acc5.update(acc5.item(), inputs.size(0))
        progress.display(it)

    return val_loss.avg, val_acc1.avg, val_acc5.avg


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Train classification of CMT model")
    parser.add_argument("--gpu_device", type = int, default = 0,
                help = "Select specific GPU to run the model")
    parser.add_argument('--batch-size', type = int, default = 64, metavar = 'N',
                help = 'Input batch size for training (default: 64)')
    parser.add_argument('--epochs', type = int, default = 20, metavar = 'N',
                help = 'Number of epochs to train (default: 20)')
    parser.add_argument('--num-class', type = int, default = 10, metavar = 'N',
                help = 'Number of classes to classify (default: 10)')
    parser.add_argument('--lr', type = float, default = 1e-3, metavar='LR',
                help = 'Learning rate (default: 0.01)')
    parser.add_argument('--weight-decay', type = float, default = 1e-5, metavar = 'WD',
                help = 'Weight decay (default: 1e-5)')
    parser.add_argument('--model-path', type = str, default = 'weights/model.pth', metavar = 'PATH',
                help = 'Path to save the model')
    args = parser.parse_args()

    # Create folder to save model
    WEIGHTS_PATH = "./weights"
    if not os.path.exists(WEIGHTS_PATH):
        os.makedirs(WEIGHTS_PATH)

    # Set device
    os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu_device)
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    # Using wandb for logging
    # wandb.init(project = "CMT: CNN meet Transformer", name = "CMT")
    # wandb.config.update(args)

    # Get Cifar10 Dataloader
    kwargs = {
        'batch_size': args.batch_size,
        'num_workers': 1,
    }
    train_loader, valid_laoder, test_loader = utils.get_dataloader(
        utils.train_transform,
        utils.test_transform,
        img_size = 224,
        **kwargs
    )

    # Create model
    net = model.CMT_B(img_size = 224, num_class = args.num_class)
    net.to(device)

    # Set loss function and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(net.parameters(), lr = args.lr,
        weight_decay = args.weight_decay
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, args.epochs)

    # Train the model
    for epoch in tqdm(range(args.epochs)):
        loss, acc1, acc5 = train_epoch(epoch, net, train_loader,
            valid_laoder, criterion, optimizer, scheduler, device
        )
        # Save model
        torch.save(net.state_dict(), args.model_path)

    print("Training is done")
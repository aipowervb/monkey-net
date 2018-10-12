import os
from tqdm import tqdm
import torch
from torch.utils.data import DataLoader
from logger import Logger, Visualizer
from modules.losses import reconstruction_loss
import numpy as np
import imageio

def reconstruction(config, generator, kp_extractor, checkpoint, log_dir, dataset):
    log_dir = os.path.join(log_dir, 'reconstruction')
    if checkpoint is not None:
        Logger.load_cpk(checkpoint, generator=generator, kp_extractor=kp_extractor)
    else:
        raise AttributeError("Checkpoint should be specified for mode='test'.")
    dataloader = DataLoader(dataset, batch_size=1, shuffle=False, num_workers=1)

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    loss_list = []
    generator.eval()
    kp_extractor.eval()
    for it, x in tqdm(enumerate(dataloader)):
        with torch.no_grad():
            kp_video = kp_extractor(x['video_array'])
            kp_appearance = {k: v[:, :1] for k, v in kp_video.items()}
            kp_dict = {'kp_video': kp_video, 'kp_appearance': kp_appearance}
            out = generator(x['video_array'][:, :, :1], **kp_dict)
            out.update(kp_dict)
            x['appearance_array'] = x['video_array'][:, :, :1]

            image = Visualizer().visualize_reconstruction(x, out)
            image_name = x['name'][0] + config['transfer_params']['format']
            imageio.mimsave(os.path.join(log_dir, image_name), image)

            loss = reconstruction_loss(out['video_prediction'].cpu(), x['video_array'].cpu(),
                                       config['loss_weights']['reconstruction'][0])
            loss_list.append(loss.data.cpu().numpy())
            del x, kp_video, kp_appearance, out, loss

    print ("Reconstruction loss: %s" % np.mean(loss_list))
